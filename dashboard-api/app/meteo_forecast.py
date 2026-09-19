"""Open-Meteo forecast client for Clima tab (no API key)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

# Andalucía approximate centroid (Sevilla basin)
LAT = 37.39
LON = -5.99
TZ = "Europe/Madrid"
CACHE_TTL_SEC = 20 * 60

_cache: dict[str, Any] = {"ts": 0.0, "payload": None}

WMO_ES: dict[int, tuple[str, str]] = {
    0: ("sunny", "Despejado"),
    1: ("partly_cloudy", "Mayormente despejado"),
    2: ("partly_cloudy", "Parcialmente nublado"),
    3: ("cloudy", "Cubierto"),
    45: ("fog", "Niebla"),
    48: ("fog", "Niebla con escarcha"),
    51: ("drizzle", "Llovizna ligera"),
    53: ("drizzle", "Llovizna"),
    55: ("drizzle", "Llovizna intensa"),
    61: ("rain", "Lluvia ligera"),
    63: ("rain", "Lluvia"),
    65: ("rain", "Lluvia intensa"),
    66: ("rain", "Lluvia helada"),
    67: ("rain", "Lluvia helada intensa"),
    71: ("snow", "Nieve ligera"),
    73: ("snow", "Nieve"),
    75: ("snow", "Nieve intensa"),
    80: ("rain", "Chubascos ligeros"),
    81: ("rain", "Chubascos"),
    82: ("rain", "Chubascos fuertes"),
    95: ("storm", "Tormenta"),
    96: ("storm", "Tormenta con granizo"),
    99: ("storm", "Tormenta fuerte con granizo"),
}


def _wmo(code: Any) -> tuple[str, str]:
    try:
        c = int(code)
    except (TypeError, ValueError):
        return "cloudy", "Sin dato"
    return WMO_ES.get(c, ("cloudy", f"Código {c}"))


def _empty(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "source": "Open-Meteo",
        "attribution": "https://open-meteo.com",
        "location_label": "Andalucía (centroide)",
        "latitude": LAT,
        "longitude": LON,
        "generated_at": None,
        "error": reason,
        "current": None,
        "hourly_today": [],
        "daily": [],
        "alerts": [],
    }


def _fetch() -> dict[str, Any]:
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TZ,
        "forecast_days": 7,
        "current": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation_probability",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
                "surface_pressure",
                "uv_index",
            ]
        ),
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation_probability",
                "weather_code",
                "apparent_temperature",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "uv_index_max",
                "wind_speed_10m_max",
            ]
        ),
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "andalucia-drought-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _forecast_alerts(current: dict[str, Any], daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    uv = current.get("uv_index")
    if uv is not None and float(uv) >= 8:
        alerts.append(
            {
                "severity": "warning",
                "code": "uv_high",
                "title_es": "Índice UV alto",
                "detail_es": f"UV actual {uv}. Protege la piel y limita exposición al mediodía.",
            }
        )
    elif uv is not None and float(uv) >= 6:
        alerts.append(
            {
                "severity": "info",
                "code": "uv_moderate",
                "title_es": "Índice UV moderado-alto",
                "detail_es": f"UV actual {uv}.",
            }
        )
    tmax = current.get("temp_c")
    if tmax is not None and float(tmax) >= 35:
        alerts.append(
            {
                "severity": "warning",
                "code": "heat_now",
                "title_es": "Temperatura elevada ahora",
                "detail_es": f"{tmax} °C (Open-Meteo).",
            }
        )
    for d in daily[:3]:
        if (d.get("uv_index_max") or 0) >= 9:
            alerts.append(
                {
                    "severity": "warning",
                    "code": "uv_day",
                    "title_es": f"UV máximo alto el {d.get('date')}",
                    "detail_es": f"UV máx {d.get('uv_index_max')}.",
                }
            )
            break
        if (d.get("t_max") or 0) >= 38:
            alerts.append(
                {
                    "severity": "critical",
                    "code": "heat_day",
                    "title_es": f"Ola de calor prevista ({d.get('date')})",
                    "detail_es": f"Tmáx {d.get('t_max')} °C.",
                }
            )
            break
    return alerts


def load_meteo_forecast() -> dict[str, Any]:
    now = time.time()
    if _cache["payload"] is not None and (now - float(_cache["ts"])) < CACHE_TTL_SEC:
        return _cache["payload"]

    try:
        raw = _fetch()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return _empty(str(exc))

    cur = raw.get("current") or {}
    code = cur.get("weather_code")
    cond, label = _wmo(code)
    current = {
        "temp_c": cur.get("temperature_2m"),
        "feels_like_c": cur.get("apparent_temperature"),
        "humidity_pct": cur.get("relative_humidity_2m"),
        "precip_probability": cur.get("precipitation_probability"),
        "pressure_hpa": cur.get("surface_pressure"),
        "wind_speed": cur.get("wind_speed_10m"),
        "wind_dir": cur.get("wind_direction_10m"),
        "uv_index": cur.get("uv_index"),
        "weather_code": code,
        "condition": cond,
        "condition_label_es": label,
        "time": cur.get("time"),
    }

    madrid = ZoneInfo(TZ)
    today = datetime.now(madrid).date().isoformat()
    hourly = raw.get("hourly") or {}
    times = hourly.get("time") or []
    hourly_today: list[dict[str, Any]] = []
    for i, t in enumerate(times):
        if not str(t).startswith(today):
            continue
        c = (hourly.get("weather_code") or [None])[i] if i < len(hourly.get("weather_code") or []) else None
        hc, hl = _wmo(c)
        hourly_today.append(
            {
                "time": t,
                "temp_c": (hourly.get("temperature_2m") or [None])[i],
                "humidity_pct": (hourly.get("relative_humidity_2m") or [None])[i],
                "precip_probability": (hourly.get("precipitation_probability") or [None])[i],
                "feels_like_c": (hourly.get("apparent_temperature") or [None])[i],
                "weather_code": c,
                "condition": hc,
                "condition_label_es": hl,
            }
        )

    daily_raw = raw.get("daily") or {}
    d_times = daily_raw.get("time") or []
    daily: list[dict[str, Any]] = []
    for i, d in enumerate(d_times):
        c = (daily_raw.get("weather_code") or [None])[i] if i < len(daily_raw.get("weather_code") or []) else None
        dc, dl = _wmo(c)
        daily.append(
            {
                "date": d,
                "t_max": (daily_raw.get("temperature_2m_max") or [None])[i],
                "t_min": (daily_raw.get("temperature_2m_min") or [None])[i],
                "precip_sum": (daily_raw.get("precipitation_sum") or [None])[i],
                "precip_probability_max": (daily_raw.get("precipitation_probability_max") or [None])[i],
                "uv_index_max": (daily_raw.get("uv_index_max") or [None])[i],
                "wind_speed_max": (daily_raw.get("wind_speed_10m_max") or [None])[i],
                "weather_code": c,
                "condition": dc,
                "condition_label_es": dl,
            }
        )

    payload = {
        "available": True,
        "source": "Open-Meteo",
        "attribution": "https://open-meteo.com",
        "location_label": "Andalucía (centroide)",
        "latitude": LAT,
        "longitude": LON,
        "generated_at": datetime.now(madrid).isoformat(),
        "error": None,
        "current": current,
        "hourly_today": hourly_today,
        "daily": daily,
        "alerts": _forecast_alerts(current, daily),
    }
    _cache["ts"] = now
    _cache["payload"] = payload
    return payload
