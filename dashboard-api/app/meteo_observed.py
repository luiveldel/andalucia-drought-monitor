"""Observed meteo from RIA (daily grain) for Clima tab."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

MARTS_SCHEMA = "marts"


def _rows(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params)
    return [dict(row._mapping) for row in result]


def _f(v: Any, nd: int = 1) -> float | None:
    if v is None:
        return None
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


def _feels_like_c(temp_c: float | None, rh: float | None) -> float | None:
    """NWS heat-index style approx when warm; otherwise return temp."""
    if temp_c is None:
        return None
    if rh is None or temp_c < 27:
        return round(temp_c, 1)
    tf = temp_c * 9.0 / 5.0 + 32.0
    r = float(rh)
    hi = (
        -42.379
        + 2.04901523 * tf
        + 10.14333127 * r
        - 0.22475541 * tf * r
        - 0.00683783 * tf * tf
        - 0.05481717 * r * r
        + 0.00122874 * tf * tf * r
        + 0.00085282 * tf * r * r
        - 0.00000199 * tf * tf * r * r
    )
    return round((hi - 32.0) * 5.0 / 9.0, 1)


def _condition(precip: float | None, radiation: float | None, humidity: float | None, tmax: float | None) -> tuple[str, str]:
    p = precip or 0.0
    rad = radiation or 0.0
    h = humidity or 50.0
    tx = tmax or 20.0
    if p >= 5:
        return "rain", "Lluvia"
    if p >= 1:
        return "cloudy", "Chubascos / nubes"
    if tx >= 35 and h <= 35:
        return "heat", "Calor extremo"
    if rad >= 25 and h < 55:
        return "sunny", "Soleado"
    if rad >= 15:
        return "partly_cloudy", "Parcialmente nublado"
    return "cloudy", "Nublado / cubierto"


def _wind_dir_label(deg: float | None) -> str | None:
    if deg is None or not math.isfinite(deg):
        return None
    dirs = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    idx = int((deg + 22.5) // 45) % 8
    return dirs[idx]


def _pack_metrics(row: dict[str, Any]) -> dict[str, Any]:
    mean_t = _f(row.get("mean_temp_c"))
    mean_h = _f(row.get("mean_humidity_pct"))
    precip = _f(row.get("precip_mm"), 2)
    rad = _f(row.get("solar_radiation"), 1)
    tmax = _f(row.get("max_temp_c"))
    wind_deg = _f(row.get("mean_wind_direction_deg"), 0)
    cond, label = _condition(precip, rad, mean_h, tmax)
    return {
        "mean_temp_c": mean_t,
        "max_temp_c": tmax,
        "min_temp_c": _f(row.get("min_temp_c")),
        "feels_like_c": _feels_like_c(mean_t, mean_h),
        "mean_humidity_pct": mean_h,
        "precip_mm": precip,
        "mean_wind_speed": _f(row.get("mean_wind_speed"), 2),
        "mean_wind_direction_deg": wind_deg,
        "wind_dir_label": _wind_dir_label(wind_deg),
        "solar_radiation": rad,
        "et0_mm": _f(row.get("et0_mm"), 2),
        "condition": cond,
        "condition_label_es": label,
        "pressure_hpa": None,
        "precip_probability": None,
        "uv_index": None,
    }


def _build_alerts(regional: dict[str, Any], by_province: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    tmax = regional.get("max_temp_c")
    humid = regional.get("mean_humidity_pct")
    precip = regional.get("precip_mm") or 0
    rad = regional.get("solar_radiation") or 0
    if tmax is not None and tmax >= 35:
        alerts.append(
            {
                "severity": "critical" if tmax >= 38 else "warning",
                "code": "heat",
                "title_es": "Calor elevado",
                "detail_es": f"Tmáx regional {tmax} °C (RIA, día observado).",
            }
        )
    if humid is not None and humid <= 30 and tmax is not None and tmax >= 32:
        alerts.append(
            {
                "severity": "warning",
                "code": "dry_heat",
                "title_es": "Calor seco",
                "detail_es": f"Humedad media {humid} % con Tmáx {tmax} °C.",
            }
        )
    if precip >= 10:
        alerts.append(
            {
                "severity": "info",
                "code": "rain",
                "title_es": "Precipitación notable",
                "detail_es": f"{precip} mm de media regional en el día.",
            }
        )
    if rad >= 28:
        alerts.append(
            {
                "severity": "warning",
                "code": "uv_proxy",
                "title_es": "Radiación alta (proxy UV)",
                "detail_es": "RIA no aporta índice UV; se usa radiación solar como aproximación.",
            }
        )
    hot_provs = [
        p["province_name"]
        for p in by_province
        if (p.get("max_temp_c") or 0) >= 35
    ]
    if len(hot_provs) >= 3:
        alerts.append(
            {
                "severity": "warning",
                "code": "heat_spread",
                "title_es": "Varias provincias con calor",
                "detail_es": ", ".join(hot_provs[:6]),
            }
        )
    return alerts


def load_meteo_observed(conn: Connection, trend_days: int = 14) -> dict[str, Any]:
    empty = {
        "available": False,
        "as_of": None,
        "grain": "daily",
        "note": "Observado RIA (diario). Sensación térmica estimada; presión/prob. precip./UV no vienen de RIA.",
        "regional": None,
        "by_province": [],
        "trend_days": [],
        "alerts": [],
    }
    try:
        latest = _rows(
            conn,
            f"""
            SELECT MAX(dd.observation_date)::text AS d
            FROM {MARTS_SCHEMA}.fact_climate_daily AS fc
            INNER JOIN {MARTS_SCHEMA}.dim_date AS dd ON fc.date_key = dd.date_key
            """,
        )
        as_of = (latest[0].get("d") if latest else None)
        if not as_of:
            return empty

        by_province = _rows(
            conn,
            f"""
            SELECT
                ds.province_name,
                ROUND(AVG(fc.mean_temperature_c)::numeric, 1)::float AS mean_temp_c,
                ROUND(AVG(fc.max_temperature_c)::numeric, 1)::float AS max_temp_c,
                ROUND(AVG(fc.min_temperature_c)::numeric, 1)::float AS min_temp_c,
                ROUND(AVG(fc.mean_humidity_pct)::numeric, 1)::float AS mean_humidity_pct,
                ROUND(AVG(fc.precipitation_mm)::numeric, 2)::float AS precip_mm,
                ROUND(AVG(fc.mean_wind_speed)::numeric, 2)::float AS mean_wind_speed,
                ROUND(AVG(fc.mean_wind_direction_deg)::numeric, 0)::float AS mean_wind_direction_deg,
                ROUND(AVG(fc.solar_radiation)::numeric, 1)::float AS solar_radiation,
                ROUND(AVG(fc.reference_evapotranspiration_mm)::numeric, 2)::float AS et0_mm
            FROM {MARTS_SCHEMA}.fact_climate_daily AS fc
            INNER JOIN {MARTS_SCHEMA}.dim_date AS dd ON fc.date_key = dd.date_key
            INNER JOIN {MARTS_SCHEMA}.dim_stations AS ds ON fc.station_key = ds.station_key
            WHERE dd.observation_date = CAST(:as_of AS date)
            GROUP BY ds.province_name
            ORDER BY ds.province_name
            """,
            as_of=as_of,
        )

        regional_rows = _rows(
            conn,
            f"""
            SELECT
                ROUND(AVG(fc.mean_temperature_c)::numeric, 1)::float AS mean_temp_c,
                ROUND(AVG(fc.max_temperature_c)::numeric, 1)::float AS max_temp_c,
                ROUND(AVG(fc.min_temperature_c)::numeric, 1)::float AS min_temp_c,
                ROUND(AVG(fc.mean_humidity_pct)::numeric, 1)::float AS mean_humidity_pct,
                ROUND(AVG(fc.precipitation_mm)::numeric, 2)::float AS precip_mm,
                ROUND(AVG(fc.mean_wind_speed)::numeric, 2)::float AS mean_wind_speed,
                ROUND(AVG(fc.mean_wind_direction_deg)::numeric, 0)::float AS mean_wind_direction_deg,
                ROUND(AVG(fc.solar_radiation)::numeric, 1)::float AS solar_radiation,
                ROUND(AVG(fc.reference_evapotranspiration_mm)::numeric, 2)::float AS et0_mm
            FROM {MARTS_SCHEMA}.fact_climate_daily AS fc
            INNER JOIN {MARTS_SCHEMA}.dim_date AS dd ON fc.date_key = dd.date_key
            WHERE dd.observation_date = CAST(:as_of AS date)
            """,
            as_of=as_of,
        )
        regional_raw = regional_rows[0] if regional_rows else {}
        regional = _pack_metrics(regional_raw)

        provinces_out = []
        for p in by_province:
            packed = _pack_metrics(p)
            packed["province_name"] = p["province_name"]
            provinces_out.append(packed)

        # Sparse RIA history: take the last N observation days that exist, not a calendar window.
        trend = _rows(
            conn,
            f"""
            WITH daily AS (
                SELECT
                    dd.observation_date,
                    ROUND(AVG(fc.mean_temperature_c)::numeric, 1)::float AS mean_temp_c,
                    ROUND(AVG(fc.mean_humidity_pct)::numeric, 1)::float AS mean_humidity_pct,
                    ROUND(AVG(fc.precipitation_mm)::numeric, 2)::float AS precip_mm
                FROM {MARTS_SCHEMA}.fact_climate_daily AS fc
                INNER JOIN {MARTS_SCHEMA}.dim_date AS dd ON fc.date_key = dd.date_key
                WHERE dd.observation_date <= CAST(:as_of AS date)
                GROUP BY dd.observation_date
            ),
            ranked AS (
                SELECT *, ROW_NUMBER() OVER (ORDER BY observation_date DESC) AS rn
                FROM daily
            )
            SELECT
                observation_date::text AS date,
                mean_temp_c,
                mean_humidity_pct,
                precip_mm
            FROM ranked
            WHERE rn <= :days
            ORDER BY observation_date
            """,
            as_of=as_of,
            days=int(trend_days),
        )

        alerts = _build_alerts(regional, provinces_out)
        return {
            "available": True,
            "as_of": as_of,
            "grain": "daily",
            "note": "Observado RIA (diario). Sensación térmica estimada; presión, probabilidad de precipitación e índice UV reales vienen del bloque Open-Meteo.",
            "regional": regional,
            "by_province": provinces_out,
            "trend_days": trend,
            "alerts": alerts,
        }
    except Exception as exc:  # noqa: BLE001 — soft-fail for dashboard
        empty["note"] = f"Error cargando RIA: {exc}"
        return empty
