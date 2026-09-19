"""Per-province climate indicator series from fact_drought_daily."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

MARTS_SCHEMA = "marts"


def _rows(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params)
    return [dict(row._mapping) for row in result]


def load_climate_by_province(conn: Connection) -> dict[str, Any]:
    """Return {province: {values + sparklines}} for Clima indicators."""
    latest = _rows(
        conn,
        f"SELECT MAX(observation_date)::text AS d FROM {MARTS_SCHEMA}.fact_drought_daily",
    )
    as_of = latest[0]["d"] if latest and latest[0].get("d") else None
    if not as_of:
        return {}

    current = _rows(
        conn,
        f"""
        SELECT
            province_name,
            ROUND(AVG(avg_fill_pct)::numeric, 1)::float AS avg_fill_pct,
            ROUND(AVG(avg_precipitation_mm)::numeric, 2)::float AS avg_precipitation_mm,
            ROUND(AVG(daily_water_deficit_mm)::numeric, 2)::float AS avg_water_deficit_mm,
            ROUND(AVG(hydric_stress_index)::numeric, 3)::float AS avg_stress
        FROM {MARTS_SCHEMA}.fact_drought_daily
        WHERE observation_date = CAST(:as_of AS date)
        GROUP BY province_name
        ORDER BY province_name
        """,
        as_of=as_of,
    )

    precip_30d = _rows(
        conn,
        f"""
        SELECT
            province_name,
            ROUND(SUM(avg_precipitation_mm)::numeric, 1)::float AS precipitation_30d_mm
        FROM {MARTS_SCHEMA}.fact_drought_daily
        WHERE observation_date >= CAST(:as_of AS date) - INTERVAL '30 days'
          AND observation_date <= CAST(:as_of AS date)
        GROUP BY province_name
        """,
        as_of=as_of,
    )
    precip_map = {r["province_name"]: r["precipitation_30d_mm"] for r in precip_30d}

    series = _rows(
        conn,
        f"""
        SELECT
            province_name,
            observation_date::text AS d,
            ROUND(AVG(avg_fill_pct)::numeric, 2)::float AS fill,
            ROUND(AVG(avg_precipitation_mm)::numeric, 2)::float AS precip,
            ROUND(AVG(daily_water_deficit_mm)::numeric, 2)::float AS deficit,
            ROUND(AVG(hydric_stress_index)::numeric, 3)::float AS stress
        FROM {MARTS_SCHEMA}.fact_drought_daily
        WHERE observation_date >= CAST(:as_of AS date) - INTERVAL '400 days'
          AND observation_date <= CAST(:as_of AS date)
        GROUP BY province_name, observation_date
        ORDER BY province_name, observation_date
        """,
        as_of=as_of,
    )

    out: dict[str, Any] = {}
    for row in current:
        name = row["province_name"]
        out[name] = {
            "avg_fill_pct": row["avg_fill_pct"],
            "avg_precipitation_mm": row["avg_precipitation_mm"],
            "avg_water_deficit_mm": row["avg_water_deficit_mm"],
            "avg_stress": row["avg_stress"],
            "precipitation_30d_mm": precip_map.get(name, 0.0),
            "sparkline_fill": [],
            "sparkline_precip": [],
            "sparkline_deficit": [],
            "sparkline_stress": [],
        }

    for row in series:
        name = row["province_name"]
        if name not in out:
            continue
        out[name]["sparkline_fill"].append({"d": row["d"], "v": row["fill"]})
        out[name]["sparkline_precip"].append({"d": row["d"], "v": row["precip"]})
        out[name]["sparkline_deficit"].append({"d": row["d"], "v": row["deficit"]})
        out[name]["sparkline_stress"].append({"d": row["d"], "v": row["stress"]})

    return out
