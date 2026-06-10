"""Read-only SQLAlchemy access to the marts (gold) schema."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

MARTS_SCHEMA = "marts"


def get_engine() -> Engine:
    host = os.environ["POSTGRES_DWH_HOST"]
    port = os.environ.get("POSTGRES_DWH_PORT", "5432")
    user = os.environ["POSTGRES_DWH_USER"]
    password = os.environ["POSTGRES_DWH_PASSWORD"]
    database = os.environ["POSTGRES_DWH_DB"]
    url = (
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    )
    return create_engine(url, pool_pre_ping=True)


def _rows(conn, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params)
    return [dict(row._mapping) for row in result]


def load_dashboard_data() -> dict[str, Any]:
    """Fetch all dashboard metrics from marts in a single connection."""
    with get_engine().connect() as conn:
        latest_date = conn.execute(
            text(
                f"""
                SELECT MAX(observation_date) AS latest_date
                FROM {MARTS_SCHEMA}.fact_drought_daily
                """
            )
        ).scalar()

        if latest_date is None:
            return {
                "latest_date": "",
                "avg_fill_pct": 0.0,
                "total_stored_hm3": 0.0,
                "provinces_in_alert": 0,
                "avg_water_deficit_mm": 0.0,
                "reservoir_status": [],
                "province_rows": [],
            }

        kpi_row = conn.execute(
            text(
                f"""
                SELECT
                    ROUND(AVG(avg_fill_pct)::numeric, 1) AS avg_fill_pct,
                    ROUND(SUM(total_stored_hm3)::numeric, 1) AS total_stored_hm3,
                    ROUND(AVG(daily_water_deficit_mm)::numeric, 2) AS avg_water_deficit_mm
                FROM {MARTS_SCHEMA}.fact_drought_daily
                WHERE observation_date = :latest_date
                """
            ),
            {"latest_date": latest_date},
        ).one()

        provinces_in_alert = conn.execute(
            text(f"SELECT COUNT(*) FROM {MARTS_SCHEMA}.fact_drought_alert")
        ).scalar() or 0

        status_rows = _rows(
            conn,
            f"""
            WITH latest AS (
                SELECT MAX(observation_date) AS observation_date
                FROM {MARTS_SCHEMA}.fact_reservoir_daily
            )
            SELECT
                CASE
                    WHEN fr.fill_percentage < 30 THEN 'Critical'
                    WHEN fr.fill_percentage < 50 THEN 'Low'
                    WHEN fr.fill_percentage < 70 THEN 'Moderate'
                    ELSE 'Good'
                END AS status,
                COUNT(*)::int AS value
            FROM {MARTS_SCHEMA}.fact_reservoir_daily AS fr
            INNER JOIN latest AS l
                ON fr.observation_date = l.observation_date
            GROUP BY 1
            ORDER BY 1
            """,
        )

        # Optimizada: Añadimos alias limpios para que coincidan con la telemetría del mapa interactivo
        province_rows = _rows(
            conn,
            f"""
            SELECT DISTINCT ON (f.province_name)
                f.province_name,
                f.province_name AS province,
                g.latitude AS lat,         -- <-- ¡Coordenada real de PostGIS!
                g.longitude AS lon,        -- <-- ¡Coordenada real de PostGIS!
                g.agricultural_area_ha,    -- Metemos el área calculada por dbt por si queremos usarla
                ROUND(f.avg_fill_pct::numeric, 1) AS avg_fill_pct,
                ROUND(f.avg_fill_pct::numeric, 1) AS fill_pct,
                ROUND(f.avg_precipitation_mm::numeric, 1) AS avg_precipitation_mm,
                ROUND(f.avg_precipitation_mm::numeric, 1) AS rain_mm,
                ROUND(f.daily_water_deficit_mm::numeric, 2) AS daily_water_deficit_mm,
                ROUND(f.daily_water_deficit_mm::numeric, 2) AS deficit_mm,
                ROUND(f.hydric_stress_index::numeric, 2) AS hydric_stress_index,
                ROUND(f.hydric_stress_index::numeric, 2) AS stress
            FROM {MARTS_SCHEMA}.fact_drought_daily f
            LEFT JOIN {MARTS_SCHEMA}.dim_provinces_geo g
                ON LOWER(TRIM(f.province_name)) = LOWER(TRIM(g.province_name))
            WHERE f.observation_date = :latest_date
            ORDER BY f.province_name, f.observation_date DESC
            """,
            latest_date=latest_date,
        )

        return {
            "latest_date": str(latest_date),
            "avg_fill_pct": float(kpi_row.avg_fill_pct or 0),
            "total_stored_hm3": float(kpi_row.total_stored_hm3 or 0),
            "provinces_in_alert": int(provinces_in_alert),
            "avg_water_deficit_mm": float(kpi_row.avg_water_deficit_mm or 0),
            "reservoir_status": status_rows,
            "province_rows": province_rows,
        }