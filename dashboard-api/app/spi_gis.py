"""SPI provisional + GIS GeoJSON helpers (marts read-only)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

MARTS = "marts"


def _rows(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params)
    return [dict(row._mapping) for row in result]


def load_spi_latest(conn: Connection) -> dict[str, Any]:
    """Latest provisional SPI snapshot per province + regional mean."""
    try:
        rows = _rows(
            conn,
            f"""
            WITH latest AS (
                SELECT MAX(month_start) AS m FROM {MARTS}.fact_spi_provisional
            )
            SELECT
                s.province_name,
                s.month_start::text AS month_start,
                s.calendar_year,
                s.calendar_month,
                ROUND(s.spi_value::numeric, 3)::float AS spi_value,
                s.spi_class_es,
                s.window_months,
                s.calibration_months,
                s.is_provisional,
                s.method_tag,
                ROUND(s.precip_window_mm::numeric, 1)::float AS precip_window_mm
            FROM {MARTS}.fact_spi_provisional AS s
            CROSS JOIN latest AS l
            WHERE s.month_start = l.m
            ORDER BY s.spi_value ASC NULLS LAST, s.province_name
            """,
        )
    except Exception:
        return {
            "available": False,
            "provisional": True,
            "caveat_es": (
                "SPI provisional no disponible: ejecuta dbt run --select fact_spi_provisional."
            ),
            "provinces": [],
            "regional_spi": None,
            "window_months": None,
            "calibration_months_max": None,
        }

    if not rows:
        return {
            "available": False,
            "provisional": True,
            "caveat_es": "Sin filas en fact_spi_provisional (serie climática vacía).",
            "provinces": [],
            "regional_spi": None,
            "window_months": None,
            "calibration_months_max": None,
        }

    vals = [float(r["spi_value"]) for r in rows if r.get("spi_value") is not None]
    calib = [int(r["calibration_months"]) for r in rows if r.get("calibration_months") is not None]
    windows = [int(r["window_months"]) for r in rows if r.get("window_months") is not None]
    max_calib = max(calib) if calib else 0
    win = max(windows) if windows else 0
    short = max_calib < 24 or win < 12

    caveat = (
        f"SPI provisional (ventana {win} mes(es); calibración máx. {max_calib} mes(es)). "
        "No es un SPI-12 WMO: la serie RIA local es corta. Úsalo solo como señal exploratoria."
        if short
        else (
            f"SPI-12 provisional con calibración corta ({max_calib} meses). "
            "Mejorará cuando haya ≥24–30 años de precipitación mensual."
        )
    )

    return {
        "available": True,
        "provisional": True,
        "caveat_es": caveat,
        "as_of_month": rows[0].get("month_start"),
        "window_months": win,
        "calibration_months_max": max_calib,
        "regional_spi": round(sum(vals) / len(vals), 3) if vals else None,
        "provinces": rows,
    }


def load_province_compare(conn: Connection, a: str, b: str) -> dict[str, Any]:
    """Side-by-side metrics for two Andalusian provinces (live marts)."""

    def one(name: str) -> dict[str, Any]:
        drought = _rows(
            conn,
            f"""
            WITH latest AS (
                SELECT MAX(observation_date) AS d FROM {MARTS}.fact_drought_daily
            ),
            cur AS (
                SELECT f.*
                FROM {MARTS}.fact_drought_daily f
                CROSS JOIN latest l
                WHERE f.observation_date = l.d
                  AND LOWER(TRIM(f.province_name)) = LOWER(TRIM(:name))
                LIMIT 1
            ),
            prev AS (
                SELECT f.avg_fill_pct AS fill_7d_ago
                FROM {MARTS}.fact_drought_daily f
                CROSS JOIN latest l
                WHERE LOWER(TRIM(f.province_name)) = LOWER(TRIM(:name))
                  AND f.observation_date = (
                    SELECT MAX(observation_date) FROM {MARTS}.fact_drought_daily
                    WHERE observation_date <= l.d - INTERVAL '7 days'
                      AND LOWER(TRIM(province_name)) = LOWER(TRIM(:name))
                  )
                LIMIT 1
            )
            SELECT
                c.province_name,
                c.observation_date::text AS observation_date,
                ROUND(c.avg_fill_pct::numeric, 1)::float AS fill_pct,
                ROUND(COALESCE(c.avg_fill_pct - p.fill_7d_ago, 0)::numeric, 1)::float AS trend_7d,
                ROUND(c.hydric_stress_index::numeric, 3)::float AS stress,
                ROUND(c.daily_water_deficit_mm::numeric, 2)::float AS deficit_mm,
                ROUND(c.avg_precipitation_mm::numeric, 2)::float AS precip_mm,
                ROUND(c.total_stored_hm3::numeric, 1)::float AS stored_hm3
            FROM cur c
            LEFT JOIN prev p ON TRUE
            """,
            name=name,
        )
        if not drought:
            return {"province": name, "found": False}

        row = drought[0]
        fill = float(row.get("fill_pct") or 0)
        if fill >= 70:
            sev = "normal"
        elif fill >= 50:
            sev = "warning"
        elif fill >= 30:
            sev = "emergency"
        else:
            sev = "critical"
        trend = float(row.get("trend_7d") or 0)
        stress = float(row.get("stress") or 0)
        risk = max(0.0, min(100.0, (100 - fill) * 0.55 + stress * 35 + max(0.0, -trend) * 3))

        spi_rows: list[dict[str, Any]] = []
        try:
            spi_rows = _rows(
                conn,
                f"""
                SELECT
                    ROUND(spi_value::numeric, 3)::float AS spi_value,
                    spi_class_es,
                    window_months,
                    calibration_months,
                    is_provisional,
                    month_start::text AS month_start
                FROM {MARTS}.fact_spi_provisional
                WHERE LOWER(TRIM(province_name)) = LOWER(TRIM(:name))
                ORDER BY month_start DESC
                LIMIT 1
                """,
                name=name,
            )
        except Exception:
            spi_rows = []

        spark = _rows(
            conn,
            f"""
            SELECT observation_date::text AS d,
                   ROUND(avg_fill_pct::numeric, 2)::float AS v
            FROM {MARTS}.fact_drought_daily
            WHERE LOWER(TRIM(province_name)) = LOWER(TRIM(:name))
              AND observation_date >= (
                  SELECT MAX(observation_date) - INTERVAL '45 days'
                  FROM {MARTS}.fact_drought_daily
              )
            ORDER BY observation_date
            """,
            name=name,
        )

        out = {
            "province": row["province_name"],
            "found": True,
            "observation_date": row.get("observation_date"),
            "fill_pct": fill,
            "severity": sev,
            "trend_7d": trend,
            "stress": stress,
            "deficit_mm": float(row.get("deficit_mm") or 0),
            "precip_mm": float(row.get("precip_mm") or 0),
            "stored_hm3": float(row.get("stored_hm3") or 0),
            "risk_score": round(risk, 1),
            "fill_sparkline": spark,
            "spi": spi_rows[0] if spi_rows else None,
        }
        return out

    left = one(a)
    right = one(b)
    return {
        "a": left,
        "b": right,
        "labels_es": {
            "fill_pct": "Llenado embalses",
            "severity": "Severidad",
            "risk_score": "Riesgo compuesto",
            "trend_7d": "Tendencia 7 días",
            "stress": "Estrés hídrico",
            "deficit_mm": "Déficit diario",
            "precip_mm": "Precipitación diaria",
            "stored_hm3": "Volumen almacenado",
            "spi": "SPI provisional",
        },
    }


def _feature_collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}


def load_provinces_geojson(conn: Connection) -> dict[str, Any]:
    """Province polygons from dim_provinces_polygons; fallback to empty FC."""
    try:
        rows = _rows(
            conn,
            f"""
            SELECT province_id, province_name, geojson, agricultural_area_ha,
                   latitude, longitude
            FROM {MARTS}.dim_provinces_polygons
            ORDER BY province_name
            """,
        )
    except Exception:
        rows = []

    features: list[dict[str, Any]] = []
    for r in rows:
        try:
            geom = json.loads(r["geojson"])
        except (TypeError, json.JSONDecodeError):
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": r["province_name"],
                    "province_id": r["province_id"],
                    "agricultural_area_ha": float(r["agricultural_area_ha"] or 0),
                    "latitude": float(r["latitude"] or 0),
                    "longitude": float(r["longitude"] or 0),
                    "layer": "province",
                },
                "geometry": geom,
            }
        )
    return _feature_collection(features)


def load_agricultural_zones_geojson(conn: Connection, simplify: float = 0.008) -> dict[str, Any]:
    """
    Raw GIS agricultural zones / province boundaries for Andalusia (cod_ccaa=01).
    Reads staging (or raw via marts staging model) with on-the-fly simplify.
    """
    # Prefer staging table built by dbt; fall back to raw if present.
    sql_candidates = [
        f"""
        SELECT
            province_id,
            province_name,
            region_id,
            ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, :tol)) AS geojson
        FROM staging.stg_gis_agricultural_zones
        WHERE region_id = '01'
           OR province_id IN ('04','11','14','18','21','23','29','41')
        """,
        f"""
        SELECT
            province_id,
            province_name,
            region_id,
            geojson
        FROM {MARTS}.dim_provinces_polygons
        """,
        """
        SELECT
            cod_prov::varchar AS province_id,
            trim(name)::varchar AS province_name,
            cod_ccaa::varchar AS region_id,
            ST_AsGeoJSON(ST_SimplifyPreserveTopology(geometry, :tol)) AS geojson
        FROM raw.raw_gis_agricultural_zones
        WHERE cod_ccaa::varchar = '01'
        """,
    ]

    rows: list[dict[str, Any]] = []
    for sql in sql_candidates:
        try:
            params: dict[str, Any] = {}
            if ":tol" in sql:
                params["tol"] = simplify
            rows = _rows(conn, sql, **params)
            if rows:
                break
        except Exception:
            continue

    features: list[dict[str, Any]] = []
    for r in rows:
        raw_g = r.get("geojson")
        if not raw_g:
            continue
        try:
            geom = json.loads(raw_g) if isinstance(raw_g, str) else raw_g
        except (TypeError, json.JSONDecodeError):
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": r.get("province_name"),
                    "province_id": r.get("province_id"),
                    "region_id": r.get("region_id"),
                    "layer": "agricultural_zone",
                },
                "geometry": geom,
            }
        )
    return _feature_collection(features)
