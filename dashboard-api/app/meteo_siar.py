"""Observed meteo from MAPA SiAR (daily grain) for Clima tab — complementary to RIA."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


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


def _wind_dir_label(deg: float | None) -> str | None:
    if deg is None or not math.isfinite(deg):
        return None
    dirs = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    idx = int((deg + 22.5) // 45) % 8
    return dirs[idx]


def _empty() -> dict[str, Any]:
    return {
        "available": False,
        "as_of": None,
        "grain": "daily",
        "source": "SiAR",
        "attribution": "https://servicio.mapa.gob.es/siarweb/",
        "note": "",
        "station_count": 0,
        "regional": None,
        "by_province": [],
        "trend_days": [],
    }


def _pack(row: dict[str, Any], *, province_name: str | None = None) -> dict[str, Any]:
    wind = _f(row.get("mean_wind"), 2)
    wind_dir = _f(row.get("mean_wind_dir"), 0)
    return {
        "province_name": province_name or row.get("province_name"),
        "station_count": int(row.get("station_count") or 0),
        "mean_temp_c": _f(row.get("mean_temp")),
        "max_temp_c": _f(row.get("max_temp")),
        "min_temp_c": _f(row.get("min_temp")),
        "mean_humidity_pct": _f(row.get("mean_humidity"), 0),
        "precip_mm": _f(row.get("mean_precip"), 2),
        "mean_wind_speed": wind,
        "mean_wind_direction_deg": wind_dir,
        "wind_dir_label": _wind_dir_label(wind_dir),
        "solar_radiation": _f(row.get("mean_radiation"), 1),
        "et0_mm": _f(row.get("mean_et0"), 2),
        "effective_precip_mm": _f(row.get("mean_pe"), 2),
    }


def load_meteo_siar(conn: Connection, trend_days: int = 14) -> dict[str, Any]:
    empty = _empty()
    try:
        latest = _rows(
            conn,
            """
            SELECT MAX(fecha)::text AS as_of
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND'
            """,
        )
        as_of = (latest[0].get("as_of") if latest else None) or None
        if not as_of:
            empty["note"] = "Sin datos SiAR en raw.raw_siar_clima_diario."
            return empty

        regional_rows = _rows(
            conn,
            """
            SELECT
                COUNT(*)::int AS station_count,
                AVG(temp_media) AS mean_temp,
                AVG(temp_max) AS max_temp,
                AVG(temp_min) AS min_temp,
                AVG(humedad_media) AS mean_humidity,
                AVG(precipitacion) AS mean_precip,
                AVG(vel_viento) AS mean_wind,
                AVG(dir_viento) AS mean_wind_dir,
                AVG(radiacion) AS mean_radiation,
                AVG(et0) AS mean_et0,
                AVG(precip_efectiva) AS mean_pe
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND' AND fecha = CAST(:as_of AS date)
            """,
            as_of=as_of,
        )
        regional = _pack(regional_rows[0]) if regional_rows else None
        if regional:
            regional["province_name"] = "Andalucía"

        prov_rows = _rows(
            conn,
            """
            SELECT
                COALESCE(provincia_nombre, 'Sin provincia') AS province_name,
                COUNT(*)::int AS station_count,
                AVG(temp_media) AS mean_temp,
                AVG(temp_max) AS max_temp,
                AVG(temp_min) AS min_temp,
                AVG(humedad_media) AS mean_humidity,
                AVG(precipitacion) AS mean_precip,
                AVG(vel_viento) AS mean_wind,
                AVG(dir_viento) AS mean_wind_dir,
                AVG(radiacion) AS mean_radiation,
                AVG(et0) AS mean_et0,
                AVG(precip_efectiva) AS mean_pe
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND' AND fecha = CAST(:as_of AS date)
            GROUP BY COALESCE(provincia_nombre, 'Sin provincia')
            ORDER BY province_name
            """,
            as_of=as_of,
        )
        by_province = [_pack(r, province_name=str(r["province_name"])) for r in prov_rows]

        trend = _rows(
            conn,
            """
            SELECT
                fecha::text AS date,
                AVG(temp_media)::float AS mean_temp_c,
                AVG(humedad_media)::float AS mean_humidity_pct,
                AVG(precipitacion)::float AS precip_mm,
                AVG(et0)::float AS et0_mm
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND'
              AND fecha > CAST(:as_of AS date) - (:days * INTERVAL '1 day')
              AND fecha <= CAST(:as_of AS date)
            GROUP BY fecha
            ORDER BY fecha
            """,
            as_of=as_of,
            days=int(trend_days),
        )
        trend_days_out = [
            {
                "date": r["date"],
                "mean_temp_c": _f(r.get("mean_temp_c")) or 0.0,
                "mean_humidity_pct": _f(r.get("mean_humidity_pct"), 0) or 0.0,
                "precip_mm": _f(r.get("precip_mm"), 2) or 0.0,
                "et0_mm": _f(r.get("et0_mm"), 2) or 0.0,
            }
            for r in trend
        ]

        return {
            "available": True,
            "as_of": as_of,
            "grain": "daily",
            "source": "SiAR",
            "attribution": "https://servicio.mapa.gob.es/siarweb/",
            "note": (
                "Observado SiAR (MAPA), red de estaciones de riego. "
                "ET0 = Penman-Monteith (EtPMon). Complementa RIA; no sustituye."
            ),
            "station_count": int((regional or {}).get("station_count") or 0),
            "regional": regional,
            "by_province": by_province,
            "trend_days": trend_days_out,
        }
    except Exception as exc:  # noqa: BLE001
        empty["note"] = f"Error cargando SiAR: {exc}"
        return empty
