"""Intraday heat spikes for irrigation demand (SiAR hourly or Open-Meteo proxy).

SiAR Web API exposes /Datos/Horarios/... (semi-hourly station records). When
raw.raw_siar_clima_horario is populated via scripts/extract_siar_hourly.py this
payload prefers that source. Otherwise we label Open-Meteo hourly as a proxy
and keep the SiAR path ready for ingest + DAG.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.provinces_meta import PROVINCES, REGIONAL_KEY

TZ = ZoneInfo("Europe/Madrid")
CACHE_TTL_SEC = 20 * 60

HEAT_TEMP_C = 35.0
HEAT_RH_PCT = 30.0
ELEVATED_TEMP_C = 32.0

_cache: dict[str, Any] = {}


def _empty(*, note: str = "") -> dict[str, Any]:
    return {
        "available": False,
        "source": "none",
        "source_label_es": "",
        "attribution": "",
        "as_of": None,
        "days": 0,
        "grain": "hourly",
        "thresholds": {
            "heat_temp_c": HEAT_TEMP_C,
            "heat_rh_pct": HEAT_RH_PCT,
            "elevated_temp_c": ELEVATED_TEMP_C,
        },
        "definition_es": (
            "Horas de estrés térmico intradía: T > 35 °C y humedad relativa < 30 % "
            "(mismo criterio que el estrés diario del mart). Una media diaria puede "
            "ocultar el pico de la tarde que dispara la demanda puntual de riego."
        ),
        "note_es": note,
        "caveats_es": [],
        "siar_ready": False,
        "siar_table": "raw.raw_siar_clima_horario",
        "headline_es": "",
        "headline_en": "",
        "regional": None,
        "by_province": [],
    }


def _hour_flags(temp: float | None, rh: float | None) -> tuple[bool, bool]:
    if temp is None:
        return False, False
    elevated = temp >= ELEVATED_TEMP_C
    heat = temp > HEAT_TEMP_C and rh is not None and rh < HEAT_RH_PCT
    return heat, elevated


def _summarize_hours(
    hours: list[dict[str, Any]],
    *,
    province_name: str,
    location_label: str,
) -> dict[str, Any]:
    temps = [h["temp_c"] for h in hours if h.get("temp_c") is not None]
    temp_mean = round(sum(temps) / len(temps), 2) if temps else None
    temp_peak = max(temps) if temps else None
    heat_n = sum(1 for h in hours if h.get("heat_stress"))
    elev_n = sum(1 for h in hours if h.get("elevated_heat"))
    et0_vals = [h["et0_mm"] for h in hours if h.get("et0_mm") is not None]
    et0_sum = round(sum(et0_vals), 3) if et0_vals else None
    rad_vals = [h["radiation"] for h in hours if h.get("radiation") is not None]
    peak_minus_mean = (
        round(temp_peak - temp_mean, 2)
        if temp_peak is not None and temp_mean is not None
        else None
    )

    dates = sorted({str(h.get("date")) for h in hours if h.get("date")})
    by_day: list[dict[str, Any]] = []
    for d in dates:
        day_hours = [h for h in hours if h.get("date") == d]
        d_temps = [h["temp_c"] for h in day_hours if h.get("temp_c") is not None]
        by_day.append(
            {
                "date": d,
                "hours": len(day_hours),
                "heat_hours": sum(1 for h in day_hours if h.get("heat_stress")),
                "elevated_hours": sum(1 for h in day_hours if h.get("elevated_heat")),
                "temp_mean_c": round(sum(d_temps) / len(d_temps), 2) if d_temps else None,
                "temp_peak_c": max(d_temps) if d_temps else None,
            }
        )

    plain_es = (
        f"En {province_name}, de las {len(hours)} horas recientes, "
        f"{heat_n} cumplen estrés térmico intradía "
        f"(T>{HEAT_TEMP_C:.0f} °C y HR<{HEAT_RH_PCT:.0f} %). "
    )
    if temp_peak is not None and temp_mean is not None and peak_minus_mean is not None:
        plain_es += (
            f"La media de esas horas es {temp_mean:.1f} °C, pero el pico llega a "
            f"{temp_peak:.1f} °C (+{peak_minus_mean:.1f} °C): el diario solo vería "
            f"la media y no el empujón de demanda de la tarde."
        )
    else:
        plain_es += "Sin temperatura suficiente para comparar pico vs media."

    plain_en = (
        f"In {province_name}, of {len(hours)} recent hours, {heat_n} meet intradaily "
        f"heat stress (T>{HEAT_TEMP_C:.0f} °C and RH<{HEAT_RH_PCT:.0f} %)."
    )
    if temp_peak is not None and temp_mean is not None and peak_minus_mean is not None:
        plain_en += (
            f" Hourly mean {temp_mean:.1f} °C vs peak {temp_peak:.1f} °C "
            f"(+{peak_minus_mean:.1f} °C); a daily mean hides the afternoon demand spike."
        )

    return {
        "province_name": province_name,
        "location_label": location_label,
        "hours_total": len(hours),
        "heat_hours": heat_n,
        "elevated_hours": elev_n,
        "temp_mean_c": temp_mean,
        "temp_peak_c": temp_peak,
        "peak_minus_mean_c": peak_minus_mean,
        "et0_sum_mm": et0_sum,
        "radiation_mean": round(sum(rad_vals) / len(rad_vals), 2) if rad_vals else None,
        "by_day": by_day,
        "series": hours,
        "plain_es": plain_es,
        "plain_en": plain_en,
    }


def _table_exists(conn: Connection, schema: str, table: str) -> bool:
    rows = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
            LIMIT 1
            """
        ),
        {"schema": schema, "table": table},
    ).fetchall()
    return bool(rows)


def _parse_hora_min(hm: int) -> tuple[int, int]:
    """SiAR HoraMin: 30, 100, 130, 200… → (hour, minute)."""
    if hm < 0:
        return 0, 0
    if hm < 100:
        return 0, hm
    return hm // 100, hm % 100


def _regional_blend(provinces_out: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for p in provinces_out:
        for h in p.get("series") or []:
            key = str(h.get("time") or "")
            if key:
                buckets.setdefault(key, []).append(h)
    out: list[dict[str, Any]] = []
    for key in sorted(buckets.keys()):
        pts = buckets[key]

        def avg(field: str, _pts: list[dict[str, Any]] = pts) -> float | None:
            vals = [p[field] for p in _pts if p.get(field) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        temp = avg("temp_c")
        rh = avg("humidity_pct")
        heat, elev = _hour_flags(temp, rh)
        sample = pts[0]
        out.append(
            {
                "date": sample.get("date"),
                "time": key,
                "hour_label": sample.get("hour_label"),
                "temp_c": temp,
                "humidity_pct": rh,
                "et0_mm": avg("et0_mm"),
                "radiation": avg("radiation"),
                "stations": sum(int(p.get("stations") or 0) for p in pts),
                "heat_stress": heat,
                "elevated_heat": elev,
            }
        )
    return out


def _load_siar_hourly(
    conn: Connection, *, lookback_days: int = 2
) -> dict[str, Any] | None:
    try:
        if not _table_exists(conn, "raw", "raw_siar_clima_horario"):
            return None
        max_row = (
            conn.execute(
                text("SELECT MAX(fecha)::text AS d FROM raw.raw_siar_clima_horario")
            )
            .mappings()
            .first()
        )
        as_of = (max_row or {}).get("d")
        if not as_of:
            return None

        rows = (
            conn.execute(
                text(
                    """
                    SELECT
                        fecha::text AS fecha,
                        hora_min::int AS hora_min,
                        provincia_nombre,
                        AVG(temp_media)::float AS temp_c,
                        AVG(humedad_media)::float AS humidity_pct,
                        AVG(radiacion)::float AS radiation,
                        AVG(et0)::float AS et0_mm,
                        COUNT(*)::int AS stations
                    FROM raw.raw_siar_clima_horario
                    WHERE fecha >= (CAST(:as_of AS date) - (:days * INTERVAL '1 day'))
                      AND fecha <= CAST(:as_of AS date)
                      AND provincia_nombre IS NOT NULL
                    GROUP BY fecha, hora_min, provincia_nombre
                    ORDER BY fecha, hora_min, provincia_nombre
                    """
                ),
                {"as_of": as_of, "days": max(0, lookback_days - 1)},
            )
            .mappings()
            .all()
        )
        if not rows:
            return None

        by_prov: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            hour, minute = _parse_hora_min(int(r["hora_min"] or 0))
            time_label = f"{hour:02d}:{minute:02d}"
            temp = r["temp_c"]
            rh = r["humidity_pct"]
            temp_f = float(temp) if temp is not None else None
            rh_f = float(rh) if rh is not None else None
            heat, elev = _hour_flags(temp_f, rh_f)
            point = {
                "date": r["fecha"],
                "time": f"{r['fecha']}T{time_label}",
                "hour_label": time_label,
                "temp_c": round(temp_f, 2) if temp_f is not None else None,
                "humidity_pct": round(rh_f, 1) if rh_f is not None else None,
                "et0_mm": round(float(r["et0_mm"]), 3) if r["et0_mm"] is not None else None,
                "radiation": round(float(r["radiation"]), 2)
                if r["radiation"] is not None
                else None,
                "stations": int(r["stations"] or 0),
                "heat_stress": heat,
                "elevated_heat": elev,
            }
            by_prov.setdefault(str(r["provincia_nombre"]), []).append(point)

        provinces_out = [
            _summarize_hours(
                hrs,
                province_name=name,
                location_label=f"{name} · SiAR horario (media estaciones)",
            )
            for name, hrs in sorted(by_prov.items())
        ]
        regional = _summarize_hours(
            _regional_blend(provinces_out),
            province_name=REGIONAL_KEY,
            location_label="Andalucía · SiAR horario (media provincial)",
        )
        heat_reg = regional["heat_hours"]
        return {
            "available": True,
            "source": "siar_hourly",
            "source_label_es": "SiAR MAPA · datos horarios / semihorarios",
            "attribution": "https://servicio.mapa.gob.es/siarweb/",
            "as_of": as_of,
            "days": lookback_days,
            "grain": "semi_hourly_or_hourly",
            "thresholds": {
                "heat_temp_c": HEAT_TEMP_C,
                "heat_rh_pct": HEAT_RH_PCT,
                "elevated_temp_c": ELEVATED_TEMP_C,
            },
            "definition_es": _empty()["definition_es"],
            "note_es": (
                "Serie intradía desde estaciones SiAR (raw.raw_siar_clima_horario). "
                "Más fina que el diario: captura el pico de la tarde que dispara demanda."
            ),
            "caveats_es": [
                "Agregación provincial = media de estaciones con dato esa hora.",
                "ET0 horario solo si la API/estación lo aporta; si no, null.",
            ],
            "siar_ready": True,
            "siar_table": "raw.raw_siar_clima_horario",
            "headline_es": (
                f"Fuente SiAR horario. Últimas horas hasta {as_of}: "
                f"{heat_reg} horas de estrés térmico intradía a escala regional."
            ),
            "headline_en": (
                f"SiAR hourly source. Through {as_of}: {heat_reg} regional "
                "intradaily heat-stress hours."
            ),
            "regional": regional,
            "by_province": provinces_out,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _fetch_open_meteo_multi(past_days: int = 1, forecast_days: int = 1) -> list[dict[str, Any]]:
    lats = ",".join(str(p["lat"]) for p in PROVINCES)
    lons = ",".join(str(p["lon"]) for p in PROVINCES)
    params = {
        "latitude": lats,
        "longitude": lons,
        "timezone": "Europe/Madrid",
        "past_days": past_days,
        "forecast_days": forecast_days,
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "et0_fao_evapotranspiration",
                "shortwave_radiation",
                "precipitation",
            ]
        ),
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": "andalucia-drought-monitor/1.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return raw
    return []


def _om_location_to_hours(
    payload: dict[str, Any], lookback_days: int
) -> list[dict[str, Any]]:
    madrid_today = datetime.now(TZ).date()
    start = madrid_today - timedelta(days=max(0, lookback_days - 1))
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    rhs = hourly.get("relative_humidity_2m") or []
    et0s = hourly.get("et0_fao_evapotranspiration") or []
    rads = hourly.get("shortwave_radiation") or []
    out: list[dict[str, Any]] = []
    for i, t in enumerate(times):
        ts = str(t)
        day = ts[:10]
        try:
            d = date.fromisoformat(day)
        except ValueError:
            continue
        if d < start or d > madrid_today:
            continue
        temp = temps[i] if i < len(temps) else None
        rh = rhs[i] if i < len(rhs) else None
        et0 = et0s[i] if i < len(et0s) else None
        rad = rads[i] if i < len(rads) else None
        temp_f = float(temp) if temp is not None else None
        rh_f = float(rh) if rh is not None else None
        heat, elev = _hour_flags(temp_f, rh_f)
        out.append(
            {
                "date": day,
                "time": ts,
                "hour_label": ts[11:16] if len(ts) >= 16 else ts,
                "temp_c": round(temp_f, 2) if temp_f is not None else None,
                "humidity_pct": round(rh_f, 1) if rh_f is not None else None,
                "et0_mm": round(float(et0), 3) if et0 is not None else None,
                "radiation": round(float(rad), 2) if rad is not None else None,
                "stations": None,
                "heat_stress": heat,
                "elevated_heat": elev,
            }
        )
    return out


def _load_open_meteo_proxy(*, lookback_days: int = 2) -> dict[str, Any]:
    cache_key = f"om_intraday_{lookback_days}"
    hit = _cache.get(cache_key)
    if hit and (time.time() - hit["ts"] < CACHE_TTL_SEC):
        return hit["payload"]

    past = max(0, lookback_days - 1)
    try:
        locations = _fetch_open_meteo_multi(past_days=past, forecast_days=1)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return _empty(note=f"Open-Meteo no disponible ({exc}).")

    provinces_out: list[dict[str, Any]] = []
    for i, meta in enumerate(PROVINCES):
        if i >= len(locations):
            break
        hours = _om_location_to_hours(locations[i], lookback_days)
        provinces_out.append(
            _summarize_hours(
                hours,
                province_name=meta["name"],
                location_label=f"{meta['name']} capital · Open-Meteo (proxy)",
            )
        )

    if not provinces_out or not any(p["hours_total"] for p in provinces_out):
        return _empty(note="Open-Meteo respondió sin horas útiles.")

    regional = _summarize_hours(
        _regional_blend(provinces_out),
        province_name=REGIONAL_KEY,
        location_label="Andalucía · media capitales Open-Meteo (proxy)",
    )
    as_of = datetime.now(TZ).date().isoformat()
    heat_reg = regional["heat_hours"]
    payload = {
        "available": True,
        "source": "open_meteo_proxy",
        "source_label_es": "Open-Meteo horario (proxy etiquetado · no es SiAR)",
        "attribution": "https://open-meteo.com",
        "as_of": as_of,
        "days": lookback_days,
        "grain": "hourly",
        "thresholds": {
            "heat_temp_c": HEAT_TEMP_C,
            "heat_rh_pct": HEAT_RH_PCT,
            "elevated_temp_c": ELEVATED_TEMP_C,
        },
        "definition_es": _empty()["definition_es"],
        "note_es": (
            "Proxy intradía con Open-Meteo (capitales provinciales) mientras no haya "
            "ingesta SiAR horaria. Sirve para ver la curva del día y contar horas de "
            "calor; no sustituye estaciones SiAR de riego."
        ),
        "caveats_es": [
            "No es dato de estación SiAR: es reanálisis/pronóstico Open-Meteo en la capital.",
            "Cuando exista SIAR_API_KEY + tarea DAG extract_siar_hourly, esta vista "
            "pasará a source=siar_hourly automáticamente.",
            "ET0 horario FAO Open-Meteo es estimado, no EtPMon SiAR.",
        ],
        "siar_ready": False,
        "siar_table": "raw.raw_siar_clima_horario",
        "headline_es": (
            f"Proxy Open-Meteo (hoy {as_of}): {heat_reg} horas de estrés térmico "
            "intradía a escala regional. Pendiente cablear SiAR horario."
        ),
        "headline_en": (
            f"Open-Meteo proxy ({as_of}): {heat_reg} regional intradaily heat-stress "
            "hours. SiAR hourly ingest still pending."
        ),
        "regional": regional,
        "by_province": provinces_out,
    }
    _cache[cache_key] = {"ts": time.time(), "payload": payload}
    return payload


def build_intraday_heat(
    conn: Connection | None = None,
    *,
    lookback_days: int = 2,
) -> dict[str, Any]:
    """Prefer SiAR hourly table; else Open-Meteo labelled proxy."""
    if conn is not None:
        siar = _load_siar_hourly(conn, lookback_days=lookback_days)
        if siar and siar.get("available"):
            return siar
    return _load_open_meteo_proxy(lookback_days=lookback_days)
