"""Climate extras for Clima tab: heat stress + exploitation systems."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

MARTS_SCHEMA = "marts"


def _rows(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params)
    return [dict(row._mapping) for row in result]


def load_heat_stress(conn: Connection, recent_days: int = 14) -> dict[str, Any]:
    """Latest heat-stress day per province + recent daily regional rollup."""
    try:
        latest_rows = _rows(
            conn,
            f"""
            WITH latest AS (
                SELECT MAX(observation_date) AS d
                FROM {MARTS_SCHEMA}.fact_heat_stress_days
            )
            SELECT
                h.observation_date::text AS observation_date,
                h.province_name,
                h.stations_in_heat_stress::int AS stations_in_heat_stress,
                ROUND(h.avg_max_temp_c::numeric, 1)::float AS avg_max_temp_c,
                ROUND(h.avg_min_humidity_pct::numeric, 1)::float AS avg_min_humidity_pct,
                ROUND(COALESCE(h.reservoir_fill_pct, 0)::numeric, 1)::float AS reservoir_fill_pct,
                ROUND(COALESCE(h.daily_water_deficit_mm, 0)::numeric, 2)::float AS daily_water_deficit_mm,
                ROUND(COALESCE(h.agricultural_risk_index, 0)::numeric, 2)::float AS agricultural_risk_index
            FROM {MARTS_SCHEMA}.fact_heat_stress_days AS h
            CROSS JOIN latest AS l
            WHERE h.observation_date = l.d
            ORDER BY h.agricultural_risk_index DESC NULLS LAST, h.province_name
            """,
        )
        recent = _rows(
            conn,
            f"""
            SELECT
                observation_date::text AS observation_date,
                COUNT(DISTINCT province_name)::int AS provinces_affected,
                SUM(stations_in_heat_stress)::int AS stations_in_heat_stress,
                ROUND(AVG(avg_max_temp_c)::numeric, 1)::float AS avg_max_temp_c,
                ROUND(AVG(agricultural_risk_index)::numeric, 2)::float AS agricultural_risk_index
            FROM {MARTS_SCHEMA}.fact_heat_stress_days
            WHERE observation_date >= (
                SELECT COALESCE(MAX(observation_date), CURRENT_DATE) - (:days * INTERVAL '1 day')
                FROM {MARTS_SCHEMA}.fact_heat_stress_days
            )
            GROUP BY observation_date
            ORDER BY observation_date DESC
            LIMIT :days
            """,
            days=recent_days,
        )
        as_of = latest_rows[0]["observation_date"] if latest_rows else None
        return {
            "available": bool(latest_rows or recent),
            "as_of": as_of,
            "latest": latest_rows,
            "recent_days": list(reversed(recent)),
        }
    except Exception:
        conn.rollback()
        return {
            "available": False,
            "as_of": None,
            "latest": [],
            "recent_days": [],
        }


def load_exploitation_systems(conn: Connection, limit: int = 12) -> dict[str, Any]:
    """Latest month of exploitation systems, lowest fill first (stress view)."""
    try:
        rows = _rows(
            conn,
            f"""
            WITH latest AS (
                SELECT calendar_year, calendar_month
                FROM {MARTS_SCHEMA}.fact_exploitation_system
                ORDER BY calendar_year DESC, calendar_month DESC
                LIMIT 1
            )
            SELECT
                e.calendar_year::int AS calendar_year,
                e.calendar_month::int AS calendar_month,
                COALESCE(NULLIF(TRIM(e.exploitation_system), ''), 'Sin sistema') AS exploitation_system,
                COALESCE(NULLIF(TRIM(e.watershed_demarcation), ''), '—') AS watershed_demarcation,
                e.active_reservoirs::int AS active_reservoirs,
                ROUND(COALESCE(e.total_stored_hm3, 0)::numeric, 1)::float AS total_stored_hm3,
                ROUND(COALESCE(e.total_capacity_hm3, 0)::numeric, 1)::float AS total_capacity_hm3,
                ROUND(COALESCE(e.system_fill_pct, 0)::numeric, 1)::float AS system_fill_pct
            FROM {MARTS_SCHEMA}.fact_exploitation_system AS e
            CROSS JOIN latest AS l
            WHERE e.calendar_year = l.calendar_year
              AND e.calendar_month = l.calendar_month
            ORDER BY e.system_fill_pct ASC NULLS LAST, e.total_stored_hm3 DESC
            LIMIT :lim
            """,
            lim=limit,
        )
        as_of = None
        if rows:
            as_of = f"{rows[0]['calendar_year']}-{int(rows[0]['calendar_month']):02d}"
        return {"available": bool(rows), "as_of": as_of, "systems": rows}
    except Exception:
        conn.rollback()
        return {"available": False, "as_of": None, "systems": []}
