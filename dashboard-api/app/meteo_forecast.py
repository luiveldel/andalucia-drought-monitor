"""Forecast for Clima tab: AEMET OpenData (preferred) with Open-Meteo fallback."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.provinces_meta import resolve_province

# Default (Andalucía): Sevilla capital as AEMET stand-in + Andalusia centroid for Open-Meteo
AEMET_MUNICIPIO = "41091"
AEMET_LOCATION_LABEL = "Andalucía · Sevilla (AEMET)"
OM_LAT = 37.39
OM_LON = -5.99
OM_LOCATION_LABEL = "Andalucía (centroide · Open-Meteo)"

TZ = "Europe/Madrid"
CACHE_TTL_SEC = 20 * 60

_cache: dict[str, dict[str, Any]] = {}

# AEMET estado cielo codes (simplified)
AEMET_SKY: dict[str, tuple[str, str]] = {
    "11": ("sunny", "Despejado"),
    "11n": ("sunny", "Despejado"),
    "12": ("partly_cloudy", "Poco nuboso"),
    "12n": ("partly_cloudy", "Poco nuboso"),
    "13": ("partly_cloudy", "Intervalos nubosos"),
    "13n": ("partly_cloudy", "Intervalos nubosos"),
    "14": ("cloudy", "Nuboso"),
    "14n": ("cloudy", "Nuboso"),
    "15": ("cloudy", "Muy nuboso"),
    "15n": ("cloudy", "Muy nuboso"),
    "16": ("cloudy", "Cubierto"),
    "16n": ("cloudy", "Cubierto"),
    "17": ("partly_cloudy", "Nubes altas"),
    "17n": ("partly_cloudy", "Nubes altas"),
    "23": ("rain", "Intervalos nubosos con lluvia"),
    "24": ("rain", "Nuboso con lluvia"),
    "25": ("rain", "Muy nuboso con lluvia"),
    "26": ("rain", "Cubierto con lluvia"),
    "43": ("rain", "Intervalos nubosos con lluvia escasa"),
    "44": ("rain", "Nuboso con lluvia escasa"),
    "45": ("rain", "Muy nuboso con lluvia escasa"),
    "46": ("rain", "Cubierto con lluvia escasa"),
    "51": ("storm", "Intervalos nubosos con tormenta"),
    "52": ("storm", "Nuboso con tormenta"),
    "53": ("storm", "Muy nuboso con tormenta"),
    "54": ("storm", "Cubierto con tormenta"),
    "61": ("rain", "Intervalos nubosos con lluvia"),
    "62": ("rain", "Nuboso con lluvia"),
    "63": ("rain", "Muy nuboso con lluvia"),
    "64": ("rain", "Cubierto con lluvia"),
}

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
    80: ("rain", "Chubascos"),
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


def _aemet_sky(code: Any, descripcion: str | None = None) -> tuple[str, str]:
    raw = str(code or "").strip()
    if raw in AEMET_SKY:
        return AEMET_SKY[raw]
    base = raw.rstrip("n")
    if base in AEMET_SKY:
        return AEMET_SKY[base]
    if descripcion:
        return "cloudy", descripcion
    return "cloudy", "Sin dato"


def _empty(reason: str, source: str = "none") -> dict[str, Any]:
    return {
        "available": False,
        "source": source,
        "attribution": "https://opendata.aemet.es/" if source.startswith("AEMET") else "https://open-meteo.com",
        "location_label": AEMET_LOCATION_LABEL if source.startswith("AEMET") else OM_LOCATION_LABEL,
        "latitude": OM_LAT,
        "longitude": OM_LON,
        "generated_at": None,
        "error": reason,
        "current": None,
        "hourly_today": [],
        "daily": [],
        "alerts": [],
    }


def _num(v: Any) -> float | None:
    if v is None or v == "" or v == "Ip":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pick_period(items: list[dict[str, Any]], prefer: tuple[str, ...] = ("12-24", "00-24", "12", "00-12")) -> dict[str, Any]:
    by_p = {str(i.get("periodo") or ""): i for i in items if isinstance(i, dict)}
    for p in prefer:
        if p in by_p:
            return by_p[p]
    return items[0] if items else {}


def _forecast_alerts(current: dict[str, Any], daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    uv = current.get("uv_index")
    if uv is not None and float(uv) >= 8:
        alerts.append(
            {
                "severity": "warning",
                "code": "uv_high",
                "title_es": "Índice UV alto",
                "detail_es": f"UV {uv}. Protege la piel y limita exposición al mediodía.",
            }
        )
    elif uv is not None and float(uv) >= 6:
        alerts.append(
            {
                "severity": "info",
                "code": "uv_moderate",
                "title_es": "Índice UV moderado-alto",
                "detail_es": f"UV {uv}.",
            }
        )
    tmax = current.get("temp_c")
    if tmax is not None and float(tmax) >= 35:
        alerts.append(
            {
                "severity": "warning",
                "code": "heat_now",
                "title_es": "Temperatura elevada",
                "detail_es": f"{tmax} °C.",
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
                    "title_es": f"Calor intenso previsto ({d.get('date')})",
                    "detail_es": f"Tmáx {d.get('t_max')} °C.",
                }
            )
            break
    return alerts


def _aemet_http(path: str, api_key: str) -> Any:
    url = f"https://opendata.aemet.es/opendata/api{path}?api_key={urllib.parse.quote(api_key)}"
    req = urllib.request.Request(url, headers={"User-Agent": "andalucia-drought-monitor/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        meta = json.loads(resp.read().decode("utf-8", errors="replace"))
    if int(meta.get("estado") or 0) != 200 or not meta.get("datos"):
        raise RuntimeError(meta.get("descripcion") or f"AEMET estado {meta.get('estado')}")
    with urllib.request.urlopen(meta["datos"], timeout=20) as resp2:
        raw = resp2.read()
    for enc in ("iso-8859-1", "utf-8", "cp1252"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise RuntimeError("No se pudo decodificar la respuesta AEMET")


def _load_aemet(api_key: str, municipio: str = AEMET_MUNICIPIO, location_label: str = AEMET_LOCATION_LABEL, lat: float = OM_LAT, lon: float = OM_LON) -> dict[str, Any]:
    madrid = ZoneInfo(TZ)
    now = datetime.now(madrid)
    today = now.date().isoformat()
    hour_now = now.hour

    diaria = _aemet_http(f"/prediccion/especifica/municipio/diaria/{municipio}", api_key)
    horaria = _aemet_http(f"/prediccion/especifica/municipio/horaria/{municipio}", api_key)

    d_item = diaria[0] if isinstance(diaria, list) and diaria else {}
    h_item = horaria[0] if isinstance(horaria, list) and horaria else {}
    d_days = (d_item.get("prediccion") or {}).get("dia") or []
    h_days = (h_item.get("prediccion") or {}).get("dia") or []

    # --- hourly today ---
    hourly_today: list[dict[str, Any]] = []
    h_today = next((d for d in h_days if str(d.get("fecha", "")).startswith(today)), h_days[0] if h_days else None)
    if h_today:
        temps = {str(x.get("periodo")): _num(x.get("value")) for x in (h_today.get("temperatura") or []) if isinstance(x, dict)}
        feels = {str(x.get("periodo")): _num(x.get("value")) for x in (h_today.get("sensTermica") or []) if isinstance(x, dict)}
        hums = {str(x.get("periodo")): _num(x.get("value")) for x in (h_today.get("humedadRelativa") or []) if isinstance(x, dict)}
        precs = {str(x.get("periodo")): _num(x.get("value")) for x in (h_today.get("precipitacion") or []) if isinstance(x, dict)}
        skies = {
            str(x.get("periodo")): x
            for x in (h_today.get("estadoCielo") or [])
            if isinstance(x, dict)
        }
        # prob precip periods like 0814
        probs = h_today.get("probPrecipitacion") or []

        def prob_for_hour(h: int) -> float | None:
            for p in probs:
                if not isinstance(p, dict):
                    continue
                per = str(p.get("periodo") or "")
                if len(per) == 4 and per.isdigit():
                    a, b = int(per[:2]), int(per[2:])
                    if a <= h < b or (a > b and (h >= a or h < b)):
                        return _num(p.get("value"))
            return None

        periods = sorted({*temps.keys(), *skies.keys()}, key=lambda x: int(x) if x.isdigit() else 99)
        for per in periods:
            if not per.isdigit():
                continue
            h = int(per)
            sky = skies.get(per) or {}
            cond, label = _aemet_sky(sky.get("value"), sky.get("descripcion"))
            hourly_today.append(
                {
                    "time": f"{today}T{h:02d}:00",
                    "temp_c": temps.get(per),
                    "humidity_pct": hums.get(per),
                    "precip_probability": prob_for_hour(h),
                    "precip_mm": precs.get(per),
                    "feels_like_c": feels.get(per),
                    "weather_code": sky.get("value"),
                    "condition": cond,
                    "condition_label_es": label,
                }
            )

    # --- current: nearest hourly point ---
    current: dict[str, Any] | None = None
    if hourly_today:
        nearest = min(
            hourly_today,
            key=lambda x: abs(int(str(x["time"])[11:13]) - hour_now),
        )
        # wind from vientoAndRachaMax for that hour if present
        wind_speed = None
        wind_dir = None
        if h_today:
            for w in h_today.get("vientoAndRachaMax") or []:
                if not isinstance(w, dict):
                    continue
                if str(w.get("periodo")) != str(int(nearest["time"][11:13])):
                    continue
                if "velocidad" in w and isinstance(w["velocidad"], list) and w["velocidad"]:
                    wind_speed = _num(w["velocidad"][0])
                if "direccion" in w and isinstance(w["direccion"], list) and w["direccion"]:
                    wind_dir = w["direccion"][0]
                break
        # UV from today's daily
        uv = None
        d_today = next((d for d in d_days if str(d.get("fecha", "")).startswith(today)), d_days[0] if d_days else None)
        if d_today:
            uv = _num(d_today.get("uvMax"))
        current = {
            "temp_c": nearest.get("temp_c"),
            "feels_like_c": nearest.get("feels_like_c"),
            "humidity_pct": nearest.get("humidity_pct"),
            "precip_probability": nearest.get("precip_probability"),
            "pressure_hpa": None,  # not in municipal forecast
            "wind_speed": wind_speed,
            "wind_dir": wind_dir,
            "uv_index": uv,
            "weather_code": nearest.get("weather_code"),
            "condition": nearest.get("condition"),
            "condition_label_es": nearest.get("condition_label_es"),
            "time": nearest.get("time"),
        }

    # --- daily 7d ---
    daily: list[dict[str, Any]] = []
    for d in d_days[:7]:
        fecha = str(d.get("fecha") or "")[:10]
        sky_list = d.get("estadoCielo") or []
        sky = _pick_period(sky_list) if isinstance(sky_list, list) else {}
        cond, label = _aemet_sky(sky.get("value"), sky.get("descripcion"))
        temp = d.get("temperatura") or {}
        prob_list = d.get("probPrecipitacion") or []
        prob = _pick_period(prob_list) if isinstance(prob_list, list) else {}
        viento_list = d.get("viento") or []
        viento = _pick_period(viento_list) if isinstance(viento_list, list) else {}
        daily.append(
            {
                "date": fecha,
                "t_max": _num(temp.get("maxima")),
                "t_min": _num(temp.get("minima")),
                "precip_sum": None,
                "precip_probability_max": _num(prob.get("value")),
                "uv_index_max": _num(d.get("uvMax")),
                "wind_speed_max": _num(viento.get("velocidad")),
                "weather_code": sky.get("value"),
                "condition": cond,
                "condition_label_es": label or sky.get("descripcion") or "—",
            }
        )

    if not current and not daily:
        raise RuntimeError("AEMET sin predicción usable")

    payload = {
        "available": True,
        "source": "AEMET",
        "attribution": "https://opendata.aemet.es/",
        "location_label": location_label,
        "latitude": lat,
        "longitude": lon,
        "generated_at": now.isoformat(),
        "error": None,
        "current": current,
        "hourly_today": hourly_today,
        "daily": daily,
        "alerts": _forecast_alerts(current or {}, daily),
    }
    return payload


def _load_open_meteo(lat: float = OM_LAT, lon: float = OM_LON, location_label: str = OM_LOCATION_LABEL) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
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
        raw = json.loads(resp.read().decode("utf-8"))

    madrid = ZoneInfo(TZ)
    today = datetime.now(madrid).date().isoformat()
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

    hourly = raw.get("hourly") or {}
    times = hourly.get("time") or []
    hourly_today: list[dict[str, Any]] = []
    for i, t in enumerate(times):
        if not str(t).startswith(today):
            continue
        codes = hourly.get("weather_code") or []
        c = codes[i] if i < len(codes) else None
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
        codes = daily_raw.get("weather_code") or []
        c = codes[i] if i < len(codes) else None
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

    return {
        "available": True,
        "source": "Open-Meteo",
        "attribution": "https://open-meteo.com",
        "location_label": location_label,
        "latitude": lat,
        "longitude": lon,
        "generated_at": datetime.now(madrid).isoformat(),
        "error": None,
        "current": current,
        "hourly_today": hourly_today,
        "daily": daily,
        "alerts": _forecast_alerts(current, daily),
    }



def _open_meteo_current_pressure(lat: float = OM_LAT, lon: float = OM_LON) -> float | None:
    """Lightweight fetch of surface pressure (hPa) for a point."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": TZ,
        "current": "surface_pressure",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "andalucia-drought-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    return _num((raw.get("current") or {}).get("surface_pressure"))


def _enrich_pressure_from_open_meteo(payload: dict[str, Any], lat: float = OM_LAT, lon: float = OM_LON) -> dict[str, Any]:
    """Fill missing pressure on AEMET (or any) forecast current from Open-Meteo."""
    current = payload.get("current")
    if not isinstance(current, dict):
        return payload
    if current.get("pressure_hpa") is not None:
        return payload
    try:
        pressure = _open_meteo_current_pressure(lat=lat, lon=lon)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, TypeError, ValueError):
        return payload
    if pressure is None:
        return payload
    current = {**current, "pressure_hpa": pressure, "pressure_source": "Open-Meteo"}
    return {**payload, "current": current}


def load_meteo_forecast(province: str | None = None) -> dict[str, Any]:
    """Load forecast for Andalucía (default) or a province capital.

    ``province`` None / Andalucía → Sevilla AEMET as regional stand-in.
    Named province → that capital's AEMET municipio (+ Open-Meteo fallback).
    """
    meta = resolve_province(province)
    if meta is None:
        cache_key = "andalucia"
        municipio = AEMET_MUNICIPIO
        aemet_label = AEMET_LOCATION_LABEL
        lat, lon = OM_LAT, OM_LON
        om_label = OM_LOCATION_LABEL
    else:
        cache_key = str(meta["name"])
        municipio = str(meta["aemet_municipio"])
        aemet_label = f"{meta['name']} capital (AEMET)"
        lat, lon = float(meta["lat"]), float(meta["lon"])
        om_label = f"{meta['name']} (Open-Meteo)"

    now = time.time()
    hit = _cache.get(cache_key)
    if hit is not None and (now - float(hit["ts"])) < CACHE_TTL_SEC and hit.get("payload"):
        return hit["payload"]

    api_key = (os.environ.get("AEMET_API_KEY") or "").strip()
    payload: dict[str, Any]

    if api_key:
        try:
            payload = _load_aemet(
                api_key,
                municipio=municipio,
                location_label=aemet_label,
                lat=lat,
                lon=lon,
            )
            payload = _enrich_pressure_from_open_meteo(payload, lat=lat, lon=lon)
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            try:
                payload = _load_open_meteo(lat=lat, lon=lon, location_label=om_label)
                payload["error"] = f"AEMET falló ({exc}); usando Open-Meteo"
            except Exception as exc2:  # noqa: BLE001
                payload = _empty(f"AEMET: {exc}; Open-Meteo: {exc2}", source="AEMET")
    else:
        try:
            payload = _load_open_meteo(lat=lat, lon=lon, location_label=om_label)
        except Exception as exc:  # noqa: BLE001
            payload = _empty(str(exc), source="Open-Meteo")

    payload["province"] = cache_key if cache_key != "andalucia" else "Andalucía"

    if payload.get("available"):
        _cache[cache_key] = {"ts": now, "payload": payload, "source": payload.get("source")}
    else:
        _cache.pop(cache_key, None)
    return payload
