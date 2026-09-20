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
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True)


def _rows(conn, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params)
    return [dict(row._mapping) for row in result]


def _pad_spark(rows: list[dict[str, Any]], fallback: float) -> list[dict[str, Any]]:
    if rows:
        return rows
    return [{"d": "—", "v": float(fallback)}]


def _severity_from_fill(fill: float) -> str:
    if fill >= 70:
        return "normal"
    if fill >= 50:
        return "warning"
    if fill >= 30:
        return "emergency"
    return "critical"


def _empty_payload() -> dict[str, Any]:
    return {
        "latest_date": "",
        "avg_fill_pct": 0.0,
        "total_stored_hm3": 0.0,
        "provinces_in_alert": 0,
        "avg_water_deficit_mm": 0.0,
        "precipitation_30d_mm": 0.0,
        "province_rows": [],
        "agricultural_severity": [{"status": "Normal", "value": 0.0}],
        "sparkline_fill": [],
        "sparkline_precip": [],
        "sparkline_deficit": [],
        "sparkline_stress": [],
        "basin_series": [],
        "monthly_precip": [],
        "temp_anomaly": [],
        "heat_stress": {"available": False, "as_of": None, "latest": [], "recent_days": []},
        "exploitation_systems": {"available": False, "as_of": None, "systems": []},
        "meteo_observed": {"available": False, "as_of": None, "grain": "daily", "note": "", "regional": None, "by_province": [], "trend_days": [], "trend_by_province": {}, "alerts": []},
        "meteo_siar": {"available": False, "as_of": None, "grain": "daily", "source": "SiAR", "attribution": "https://servicio.mapa.gob.es/siarweb/", "note": "", "station_count": 0, "regional": None, "by_province": [], "trend_days": []},
        "irrigation_autonomy": {"available": False, "as_of_reservoir": None, "as_of_siar": None, "kc": None, "irrigated_ha_source": "", "storage_scope": "", "note": "", "method_es": "", "regional": None, "by_province": [], "alerts": [], "projection": {"available": False}, "ria_siar_compare": {"available": False}},
        "meteo_forecast": {"available": False, "source": "Open-Meteo", "attribution": "https://open-meteo.com", "location_label": "Andalucía (centroide)", "latitude": 37.39, "longitude": -5.99, "generated_at": None, "error": None, "current": None, "hourly_today": [], "daily": [], "alerts": []},
        "stress_evolution": [],
        "climate_by_province": {},
        "reservoir_rows": [],
        "province_map_kpis": [],
        "weekly_deltas": {
            "fill_pct": 0.0,
            "stored_hm3": 0.0,
            "precip_mm": 0.0,
            "deficit_mm": 0.0,
        },
        "weekly_narrative": "Sin datos en marts. Ejecuta los DAGs de Airflow y dbt run.",
        "alerts": [],
        "recommendations": [
            {
                "priority": "info",
                "title": "Poblar el almacén",
                "detail": "Lanza elt_daily_pipeline y elt_monthly_pipeline, luego dbt run.",
            }
        ],
        "risk_board": [],
        "data_notes": [
            "Precipitación = avg_precipitation_mm (mm).",
            "Déficit hídrico = daily_water_deficit_mm (ET0 − precip), no SPI-12.",
            "SPI-12 pendiente de climatología histórica en marts.",
        ],
    }


def _build_alerts(province_rows: list[dict[str, Any]], avg_fill: float, precip_30d: float) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for p in province_rows:
        fill = float(p.get("avg_fill_pct") or 0)
        name = p.get("province_name") or p.get("province") or "?"
        sev = _severity_from_fill(fill)
        if sev in ("critical", "emergency"):
            alerts.append(
                {
                    "id": f"fill-{name}",
                    "severity": sev,
                    "province": name,
                    "title": f"{name}: llenado {fill:.1f}%",
                    "detail": "Restricción de riego no esencial y priorizar usos urbanos/agrícolas críticos.",
                    "metric": "fill_pct",
                    "value": fill,
                }
            )
        deficit = float(p.get("daily_water_deficit_mm") or 0)
        if deficit >= 4:
            alerts.append(
                {
                    "id": f"deficit-{name}",
                    "severity": "warning" if deficit < 6 else "emergency",
                    "province": name,
                    "title": f"{name}: déficit {deficit:.1f} mm/día",
                    "detail": "ET0 supera la precipitación; revisar turnos de riego y cultivos sensibles.",
                    "metric": "deficit_mm",
                    "value": deficit,
                }
            )
    if avg_fill < 40:
        alerts.append(
            {
                "id": "regional-fill",
                "severity": "critical" if avg_fill < 30 else "emergency",
                "province": "Andalucía",
                "title": f"Llenado regional bajo ({avg_fill:.1f}%)",
                "detail": "Activar mesa de sequía y comunicar escenarios a comunidades de regantes.",
                "metric": "avg_fill_pct",
                "value": avg_fill,
            }
        )
    if precip_30d < 20:
        alerts.append(
            {
                "id": "precip-30d",
                "severity": "warning",
                "province": "Andalucía",
                "title": f"Lluvia 30d escasa ({precip_30d:.1f} mm)",
                "detail": "Escenario seco a corto plazo; vigilar embalses de cabecera.",
                "metric": "precipitation_30d_mm",
                "value": precip_30d,
            }
        )
    order = {"critical": 0, "emergency": 1, "warning": 2, "normal": 3}
    alerts.sort(key=lambda a: (order.get(a["severity"], 9), a["title"]))
    return alerts[:12]


def _build_recommendations(alerts: list[dict[str, Any]], risk_board: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    critical = [a for a in alerts if a["severity"] == "critical"]
    if critical:
        names = ", ".join(sorted({a["province"] for a in critical})[:4])
        recs.append(
            {
                "priority": "high",
                "title": "Priorizar provincias en crítico",
                "detail": f"Foco operativo en: {names}. Validar caudales ecológicos y reservas estratégicas.",
            }
        )
    declining = [r for r in risk_board if float(r.get("trend_7d") or 0) <= -2]
    if declining:
        names = ", ".join(r["province"] for r in declining[:3])
        recs.append(
            {
                "priority": "medium",
                "title": "Caída rápida de reservas (7d)",
                "detail": f"{names}: analizar extracciones y pérdidas; contrastar con aportaciones.",
            }
        )
    if not recs:
        recs.append(
            {
                "priority": "info",
                "title": "Mantener vigilancia semanal",
                "detail": "Sin alertas críticas; revisar ranking provincial y lluvia acumulada cada lunes.",
            }
        )
    return recs


def _weekly_narrative(deltas: dict[str, float], avg_fill: float, alert_n: int) -> str:
    df = deltas.get("fill_pct", 0.0)
    ds = deltas.get("stored_hm3", 0.0)
    dp = deltas.get("precip_mm", 0.0)
    direction = "subió" if df >= 0 else "bajó"
    return (
        f"Esta semana el llenado medio {direction} {abs(df):.1f} pp "
        f"(ahora {avg_fill:.1f}%). Volumen almacenado Δ {ds:+.1f} hm³; "
        f"precipitación media diaria Δ {dp:+.2f} mm. "
        f"Provincias en alerta/emergencia: {alert_n}."
    )


def load_dashboard_data() -> dict[str, Any]:
    """Fetch dashboard metrics from marts in a single connection."""
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
            return _empty_payload()

        kpi_row = conn.execute(
            text(
                f"""
                SELECT
                    ROUND(AVG(avg_fill_pct)::numeric, 1) AS avg_fill_pct,
                    ROUND(SUM(total_stored_hm3)::numeric, 1) AS total_stored_hm3,
                    ROUND(AVG(daily_water_deficit_mm)::numeric, 2) AS avg_water_deficit_mm,
                    ROUND(AVG(avg_precipitation_mm)::numeric, 2) AS avg_precipitation_mm,
                    ROUND(AVG(hydric_stress_index)::numeric, 3) AS avg_stress
                FROM {MARTS_SCHEMA}.fact_drought_daily
                WHERE observation_date = :latest_date
                """
            ),
            {"latest_date": latest_date},
        ).one()

        week_ago = conn.execute(
            text(
                f"""
                SELECT
                    ROUND(AVG(avg_fill_pct)::numeric, 1) AS avg_fill_pct,
                    ROUND(SUM(total_stored_hm3)::numeric, 1) AS total_stored_hm3,
                    ROUND(AVG(avg_precipitation_mm)::numeric, 2) AS avg_precipitation_mm,
                    ROUND(AVG(daily_water_deficit_mm)::numeric, 2) AS avg_water_deficit_mm
                FROM {MARTS_SCHEMA}.fact_drought_daily
                WHERE observation_date = (
                    SELECT MAX(observation_date)
                    FROM {MARTS_SCHEMA}.fact_drought_daily
                    WHERE observation_date <= :latest_date - INTERVAL '7 days'
                )
                """
            ),
            {"latest_date": latest_date},
        ).one_or_none()

        try:
            alert_count = conn.execute(
                text(
                    f"""
                    SELECT COUNT(DISTINCT province_name)::int AS c
                    FROM {MARTS_SCHEMA}.fact_drought_alert
                    """
                )
            ).scalar() or 0
        except Exception:
            # mart may be absent until dbt builds drought alerts
            conn.rollback()
            alert_count = 0

        precip_30d = conn.execute(
            text(
                f"""
                WITH dr AS (
                    SELECT observation_date, AVG(avg_precipitation_mm) AS daily_precip
                    FROM {MARTS_SCHEMA}.fact_drought_daily
                    WHERE observation_date >= :latest_date - INTERVAL '30 days'
                    GROUP BY observation_date
                )
                SELECT COALESCE(ROUND(SUM(daily_precip)::numeric, 1), 0)::float AS s
                FROM dr
                """
            ),
            {"latest_date": latest_date},
        ).scalar() or 0.0

        agricultural_severity = _rows(
            conn,
            f"""
            WITH latest AS (
                SELECT MAX(observation_date) AS d FROM {MARTS_SCHEMA}.fact_drought_daily
            ),
            prov AS (
                SELECT
                    f.province_name,
                    f.avg_fill_pct,
                    COALESCE(g.agricultural_area_ha, 0)::float AS ha
                FROM {MARTS_SCHEMA}.fact_drought_daily AS f
                LEFT JOIN {MARTS_SCHEMA}.dim_provinces_geo AS g
                    ON LOWER(TRIM(f.province_name)) = LOWER(TRIM(g.province_name))
                CROSS JOIN latest AS l
                WHERE f.observation_date = l.d
            ),
            bucketed AS (
                SELECT
                    CASE
                        WHEN avg_fill_pct >= 70 THEN 'Normal'
                        WHEN avg_fill_pct >= 50 THEN 'Alert'
                        WHEN avg_fill_pct >= 30 THEN 'Emergency'
                        ELSE 'Critical'
                    END AS status,
                    SUM(ha)::float AS value
                FROM prov
                GROUP BY 1
            )
            SELECT status, ROUND(value::numeric, 1)::float AS value
            FROM bucketed
            ORDER BY status
            """,
        )

        province_rows = _rows(
            conn,
            f"""
            SELECT DISTINCT ON (f.province_name)
                f.province_name,
                f.province_name AS province,
                g.latitude AS lat,
                g.longitude AS lon,
                g.agricultural_area_ha,
                ROUND(f.avg_fill_pct::numeric, 1) AS avg_fill_pct,
                ROUND(f.avg_fill_pct::numeric, 1) AS fill_pct,
                ROUND(f.avg_precipitation_mm::numeric, 1) AS avg_precipitation_mm,
                ROUND(f.avg_precipitation_mm::numeric, 1) AS rain_mm,
                ROUND(f.daily_water_deficit_mm::numeric, 2) AS daily_water_deficit_mm,
                ROUND(f.daily_water_deficit_mm::numeric, 2) AS deficit_mm,
                ROUND(f.hydric_stress_index::numeric, 2) AS hydric_stress_index,
                ROUND(f.hydric_stress_index::numeric, 2) AS stress
            FROM {MARTS_SCHEMA}.fact_drought_daily AS f
            LEFT JOIN {MARTS_SCHEMA}.dim_provinces_geo AS g
                ON LOWER(TRIM(f.province_name)) = LOWER(TRIM(g.province_name))
            WHERE f.observation_date = :latest_date
            ORDER BY f.province_name, f.observation_date DESC
            """,
            latest_date=latest_date,
        )

        # Prefer dbt mart (sensible 0–100 weights). Fallback recomputes the same heuristic.
        try:
            risk_board = _rows(
                conn,
                f"""
                WITH latest AS (
                    SELECT MAX(observation_date) AS d
                    FROM {MARTS_SCHEMA}.fact_province_risk_daily
                ),
                cur AS (
                    SELECT r.*
                    FROM {MARTS_SCHEMA}.fact_province_risk_daily AS r
                    CROSS JOIN latest AS l
                    WHERE r.observation_date = l.d
                ),
                prev AS (
                    SELECT
                        f.province_name,
                        AVG(f.avg_fill_pct)::float AS fill_7d_ago
                    FROM {MARTS_SCHEMA}.fact_drought_daily AS f
                    CROSS JOIN latest AS l
                    WHERE f.observation_date = (
                        SELECT MAX(observation_date)
                        FROM {MARTS_SCHEMA}.fact_drought_daily
                        WHERE observation_date <= l.d - INTERVAL '7 days'
                    )
                    GROUP BY f.province_name
                )
                SELECT
                    c.province_name AS province,
                    ROUND(c.avg_fill_pct::numeric, 1)::float AS fill_pct,
                    ROUND(COALESCE(c.avg_fill_pct - p.fill_7d_ago, 0)::numeric, 1)::float AS trend_7d,
                    ROUND(c.hydric_stress_index::numeric, 3)::float AS stress,
                    ROUND(c.daily_water_deficit_mm::numeric, 2)::float AS deficit_mm,
                    ROUND(c.risk_score::numeric, 1)::float AS risk_score,
                    c.severity AS risk_band
                FROM cur AS c
                LEFT JOIN prev AS p ON c.province_name = p.province_name
                ORDER BY c.risk_score DESC, c.avg_fill_pct ASC
                """,
            )
        except Exception:
            conn.rollback()
            risk_board = []

        if not risk_board:
            risk_board = _rows(
                conn,
                f"""
                WITH latest AS (
                    SELECT MAX(observation_date) AS d FROM {MARTS_SCHEMA}.fact_drought_daily
                ),
                cur AS (
                    SELECT
                        f.province_name,
                        AVG(f.avg_fill_pct)::float AS avg_fill_pct,
                        AVG(f.hydric_stress_index)::float AS hydric_stress_index,
                        AVG(f.daily_water_deficit_mm)::float AS daily_water_deficit_mm
                    FROM {MARTS_SCHEMA}.fact_drought_daily f
                    CROSS JOIN latest l
                    WHERE f.observation_date = l.d
                    GROUP BY f.province_name
                ),
                prev AS (
                    SELECT
                        f.province_name,
                        AVG(f.avg_fill_pct)::float AS fill_7d_ago
                    FROM {MARTS_SCHEMA}.fact_drought_daily f
                    CROSS JOIN latest l
                    WHERE f.observation_date = (
                        SELECT MAX(observation_date) FROM {MARTS_SCHEMA}.fact_drought_daily
                        WHERE observation_date <= l.d - INTERVAL '7 days'
                    )
                    GROUP BY f.province_name
                )
                SELECT
                    c.province_name AS province,
                    ROUND(c.avg_fill_pct::numeric, 1)::float AS fill_pct,
                    ROUND(COALESCE(c.avg_fill_pct - p.fill_7d_ago, 0)::numeric, 1)::float AS trend_7d,
                    ROUND(c.hydric_stress_index::numeric, 3)::float AS stress,
                    ROUND(c.daily_water_deficit_mm::numeric, 2)::float AS deficit_mm
                FROM cur c
                LEFT JOIN prev p ON c.province_name = p.province_name
                ORDER BY c.avg_fill_pct ASC
                """,
            )
            for r in risk_board:
                fill = float(r.get("fill_pct") or 0)
                stress = float(r.get("stress") or 0)
                deficit = float(r.get("deficit_mm") or 0)
                # Same weights as fact_province_risk_daily (do NOT multiply raw stress by 35).
                risk = (
                    0.50 * max(0.0, min(100.0, 100.0 - fill))
                    + 0.35 * max(0.0, min(100.0, deficit * 12.0))
                    + 0.15 * max(0.0, min(100.0, abs(stress) * 25.0))
                )
                r["risk_score"] = round(risk, 1)

        for r in risk_board:
            r["severity"] = _severity_from_fill(float(r.get("fill_pct") or 0))

        # Same metric as KPI avg_fill_pct (province rollup in fact_drought_daily).
        # Wide window: embalses/drought snapshots are sparse, so 45d often yields 1 point.
        sparkline_fill = _rows(
            conn,
            f"""
            SELECT observation_date::text AS d, ROUND(AVG(avg_fill_pct)::numeric, 2)::float AS v
            FROM {MARTS_SCHEMA}.fact_drought_daily
            WHERE observation_date >= :latest_date - INTERVAL '400 days'
            GROUP BY observation_date
            ORDER BY observation_date
            """,
            latest_date=latest_date,
        )

        sparkline_precip = _rows(
            conn,
            f"""
            SELECT observation_date::text AS d, ROUND(AVG(avg_precipitation_mm)::numeric, 2)::float AS v
            FROM {MARTS_SCHEMA}.fact_drought_daily
            WHERE observation_date >= :latest_date - INTERVAL '400 days'
            GROUP BY observation_date
            ORDER BY observation_date
            """,
            latest_date=latest_date,
        )

        sparkline_deficit = _rows(
            conn,
            f"""
            SELECT observation_date::text AS d, ROUND(AVG(daily_water_deficit_mm)::numeric, 2)::float AS v
            FROM {MARTS_SCHEMA}.fact_drought_daily
            WHERE observation_date >= :latest_date - INTERVAL '400 days'
            GROUP BY observation_date
            ORDER BY observation_date
            """,
            latest_date=latest_date,
        )

        sparkline_stress = _rows(
            conn,
            f"""
            SELECT observation_date::text AS d, ROUND(AVG(hydric_stress_index)::numeric, 3)::float AS v
            FROM {MARTS_SCHEMA}.fact_drought_daily
            WHERE observation_date >= :latest_date - INTERVAL '400 days'
            GROUP BY observation_date
            ORDER BY observation_date
            """,
            latest_date=latest_date,
        )

        basin_series = _rows(
            conn,
            f"""
            WITH b AS (
                SELECT
                    hydrological_year,
                    CASE
                        WHEN watershed_demarcation IS NULL THEN 'Other'
                        WHEN LOWER(watershed_demarcation) LIKE '%guadalquivir%' THEN 'Guadalquivir'
                        WHEN LOWER(watershed_demarcation) LIKE '%atlántico%'
                            OR LOWER(watershed_demarcation) LIKE '%sur%'
                            OR LOWER(watershed_demarcation) LIKE '%mediterr%'
                            OR LOWER(watershed_demarcation) LIKE '%andaluz%'
                            THEN 'South'
                        ELSE 'Other'
                    END AS basin_bucket,
                    AVG(avg_fill_pct)::float AS avg_fill_pct
                FROM {MARTS_SCHEMA}.fact_hydrological_year
                GROUP BY 1, 2
            ),
            means AS (
                SELECT basin_bucket, AVG(avg_fill_pct)::float AS hist_mean
                FROM b
                GROUP BY 1
            )
            SELECT
                b.hydrological_year,
                b.basin_bucket,
                ROUND(b.avg_fill_pct::numeric, 2)::float AS avg_fill_pct,
                ROUND(m.hist_mean::numeric, 2)::float AS hist_mean
            FROM b
            INNER JOIN means AS m ON b.basin_bucket = m.basin_bucket
            WHERE b.basin_bucket IN ('Guadalquivir', 'South')
            ORDER BY b.hydrological_year, b.basin_bucket
            """,
        )

        monthly_precip = _rows(
            conn,
            f"""
            SELECT
                dd.calendar_year,
                dd.calendar_month,
                ROUND(AVG(fc.precipitation_mm)::numeric, 2)::float AS avg_mm
            FROM {MARTS_SCHEMA}.fact_climate_daily AS fc
            INNER JOIN {MARTS_SCHEMA}.dim_date AS dd ON fc.date_key = dd.date_key
            WHERE dd.calendar_year IN (2025, 2026)
            GROUP BY dd.calendar_year, dd.calendar_month
            ORDER BY dd.calendar_year, dd.calendar_month
            """,
        )

        temp_anomaly = _rows(
            conn,
            f"""
            WITH daily AS (
                SELECT
                    dd.calendar_year,
                    dd.calendar_month,
                    dd.calendar_day,
                    AVG(fc.mean_temperature_c) AS t
                FROM {MARTS_SCHEMA}.fact_climate_daily AS fc
                INNER JOIN {MARTS_SCHEMA}.dim_date AS dd ON fc.date_key = dd.date_key
                GROUP BY dd.calendar_year, dd.calendar_month, dd.calendar_day
            ),
            monthly AS (
                SELECT calendar_year, calendar_month, AVG(t)::float AS avg_temp
                FROM daily
                GROUP BY calendar_year, calendar_month
            ),
            baseline AS (
                SELECT calendar_month, AVG(avg_temp)::float AS baseline_temp
                FROM monthly
                WHERE calendar_year >= EXTRACT(YEAR FROM CURRENT_DATE)::int - 15
                  AND calendar_year < EXTRACT(YEAR FROM CURRENT_DATE)::int
                GROUP BY calendar_month
            )
            SELECT
                m.calendar_year,
                m.calendar_month,
                ROUND(m.avg_temp::numeric, 2)::float AS avg_temp,
                ROUND(b.baseline_temp::numeric, 2)::float AS baseline_temp,
                ROUND((m.avg_temp - b.baseline_temp)::numeric, 2)::float AS anomaly
            FROM monthly AS m
            INNER JOIN baseline AS b ON m.calendar_month = b.calendar_month
            WHERE m.calendar_year >= EXTRACT(YEAR FROM CURRENT_DATE)::int - 1
            ORDER BY m.calendar_year, m.calendar_month
            """,
        )

        from app.climate_extras import load_exploitation_systems, load_heat_stress
        from app.meteo_observed import load_meteo_observed
        from app.meteo_siar import load_meteo_siar
        from app.irrigation_autonomy import load_irrigation_autonomy
        from app.meteo_forecast import load_meteo_forecast

        heat_stress = load_heat_stress(conn)
        exploitation_systems = load_exploitation_systems(conn)
        meteo_observed = load_meteo_observed(conn)
        meteo_siar = load_meteo_siar(conn)
        irrigation_autonomy = load_irrigation_autonomy(conn)
        from app.climate_by_province import load_climate_by_province
        climate_by_province = load_climate_by_province(conn)
        meteo_forecast = load_meteo_forecast()

        stress_evolution = _rows(
            conn,
            f"""
            SELECT observation_date::text AS d, ROUND(AVG(hydric_stress_index)::numeric, 3)::float AS v
            FROM {MARTS_SCHEMA}.fact_drought_daily
            WHERE observation_date >= :latest_date - INTERVAL '400 days'
            GROUP BY observation_date
            ORDER BY observation_date
            """,
            latest_date=latest_date,
        )

        reservoir_rows = _rows(
            conn,
            f"""
            WITH latest AS (
                SELECT MAX(observation_date) AS d FROM {MARTS_SCHEMA}.fact_reservoir_daily
            ),
            ranked AS (
                SELECT
                    dr.reservoir_name,
                    dr.province_name,
                    COALESCE(dr.watershed_demarcation, '—') AS basin,
                    COALESCE(dr.reservoir_capacity_hm3, 0)::float AS capacity_hm3,
                    fr.fill_percentage,
                    fr.observation_date,
                    LAG(fr.fill_percentage, 7) OVER (
                        PARTITION BY fr.reservoir_key ORDER BY fr.observation_date
                    ) AS prev_7d
                FROM {MARTS_SCHEMA}.fact_reservoir_daily AS fr
                INNER JOIN {MARTS_SCHEMA}.dim_reservoirs AS dr ON dr.reservoir_key = fr.reservoir_key
            )
            SELECT
                r.reservoir_name,
                r.province_name AS province,
                r.basin,
                ROUND(r.capacity_hm3::numeric, 1)::float AS capacity_hm3,
                ROUND((r.capacity_hm3 * r.fill_percentage / 100.0)::numeric, 1)::float AS current_hm3,
                ROUND(r.fill_percentage::numeric, 1)::float AS fill_pct,
                CASE
                    WHEN r.prev_7d IS NULL THEN NULL
                    ELSE ROUND((r.fill_percentage - r.prev_7d)::numeric, 1)::float
                END AS delta_7d
            FROM ranked AS r
            CROSS JOIN latest AS l
            WHERE r.observation_date = l.d
            ORDER BY r.fill_percentage ASC, r.reservoir_name
            """,
        )

        for row in reservoir_rows:
            dv = row.get("delta_7d")
            if dv is None:
                row["delta_7d"] = ""
                row["delta_dir"] = "flat"
                row["weekly_change"] = 0.0
            else:
                f_delta = float(dv)
                row["delta_7d"] = f"{f_delta:+.1f}"
                row["delta_dir"] = "up" if f_delta >= 0 else "down"
                row["weekly_change"] = f_delta
            fp = float(row.get("fill_pct") or 0)
            row["status"] = _severity_from_fill(fp)
            if fp < 30:
                row["fill_bar_tone"] = "critical"
            elif fp < 50:
                row["fill_bar_tone"] = "emergency"
            elif fp < 70:
                row["fill_bar_tone"] = "alert"
            else:
                row["fill_bar_tone"] = "normal"

        if not agricultural_severity:
            agricultural_severity = [{"status": "Normal", "value": 0.0}]

        avg_fill = float(kpi_row.avg_fill_pct or 0)
        sparkline_fill = _pad_spark(sparkline_fill, avg_fill)
        sparkline_precip = _pad_spark(sparkline_precip, float(kpi_row.avg_precipitation_mm or 0))
        sparkline_deficit = _pad_spark(sparkline_deficit, float(kpi_row.avg_water_deficit_mm or 0))
        sparkline_stress = _pad_spark(sparkline_stress, float(kpi_row.avg_stress or 0))

        province_map_kpis = _rows(
            conn,
            f"""
            WITH latest AS (
                SELECT MAX(observation_date) AS d FROM {MARTS_SCHEMA}.fact_drought_daily
            ),
            drought AS (
                SELECT DISTINCT ON (f.province_name)
                    f.province_name,
                    ROUND(f.avg_fill_pct::numeric, 1)::float AS fill_pct
                FROM {MARTS_SCHEMA}.fact_drought_daily AS f
                CROSS JOIN latest AS l
                WHERE f.observation_date = l.d
                ORDER BY f.province_name, f.observation_date DESC
            ),
            rs AS (
                SELECT
                    TRIM(province_name) AS province_key,
                    COUNT(*)::int AS reservoir_count,
                    COALESCE(SUM(reservoir_capacity_hm3), 0)::float AS reservoir_capacity_hm3_sum
                FROM {MARTS_SCHEMA}.dim_reservoirs
                WHERE province_name IS NOT NULL AND TRIM(province_name) <> ''
                GROUP BY TRIM(province_name)
            ),
            st AS (
                SELECT
                    TRIM(province_name) AS province_key,
                    COUNT(*)::int AS station_count
                FROM {MARTS_SCHEMA}.dim_stations
                WHERE province_name IS NOT NULL AND TRIM(province_name) <> ''
                GROUP BY TRIM(province_name)
            )
            SELECT
                g.province_id,
                g.province_name,
                ROUND(g.latitude::numeric, 5)::float AS latitude,
                ROUND(g.longitude::numeric, 5)::float AS longitude,
                ROUND(g.agricultural_area_ha::numeric, 1)::float AS agricultural_area_ha,
                COALESCE(rs.reservoir_count, 0)::int AS reservoir_count,
                ROUND(COALESCE(rs.reservoir_capacity_hm3_sum, 0)::numeric, 2)::float AS reservoir_capacity_hm3_sum,
                COALESCE(st.station_count, 0)::int AS station_count,
                COALESCE(d.fill_pct, 0)::float AS fill_pct
            FROM {MARTS_SCHEMA}.dim_provinces_geo AS g
            LEFT JOIN rs ON LOWER(rs.province_key) = LOWER(TRIM(g.province_name))
            LEFT JOIN st ON LOWER(st.province_key) = LOWER(TRIM(g.province_name))
            LEFT JOIN drought AS d ON LOWER(TRIM(d.province_name)) = LOWER(TRIM(g.province_name))
            ORDER BY g.province_name
            """,
        )

        if week_ago is None:
            weekly_deltas = {
                "fill_pct": 0.0,
                "stored_hm3": 0.0,
                "precip_mm": 0.0,
                "deficit_mm": 0.0,
            }
        else:
            weekly_deltas = {
                "fill_pct": round(avg_fill - float(week_ago.avg_fill_pct or 0), 1),
                "stored_hm3": round(
                    float(kpi_row.total_stored_hm3 or 0) - float(week_ago.total_stored_hm3 or 0), 1
                ),
                "precip_mm": round(
                    float(kpi_row.avg_precipitation_mm or 0)
                    - float(week_ago.avg_precipitation_mm or 0),
                    2,
                ),
                "deficit_mm": round(
                    float(kpi_row.avg_water_deficit_mm or 0)
                    - float(week_ago.avg_water_deficit_mm or 0),
                    2,
                ),
            }

        alerts = _build_alerts(province_rows, avg_fill, float(precip_30d))
        # count provinces in emergency+ from fill if alert table empty
        prov_alert_n = sum(
            1 for p in province_rows if _severity_from_fill(float(p.get("avg_fill_pct") or 0)) in ("emergency", "critical")
        )
        effective_alerts = max(int(alert_count), prov_alert_n)
        recommendations = _build_recommendations(alerts, risk_board)
        narrative = _weekly_narrative(weekly_deltas, avg_fill, effective_alerts)

        return {
            "latest_date": str(latest_date),
            "avg_fill_pct": avg_fill,
            "total_stored_hm3": float(kpi_row.total_stored_hm3 or 0),
            "provinces_in_alert": effective_alerts,
            "avg_water_deficit_mm": float(kpi_row.avg_water_deficit_mm or 0),
            "avg_precipitation_mm": float(kpi_row.avg_precipitation_mm or 0),
            "avg_stress": float(kpi_row.avg_stress or 0),
            "precipitation_30d_mm": float(precip_30d),
            "province_rows": province_rows,
            "agricultural_severity": agricultural_severity,
            "sparkline_fill": sparkline_fill,
            "sparkline_precip": sparkline_precip,
            "sparkline_deficit": sparkline_deficit,
            "sparkline_stress": sparkline_stress,
            "basin_series": basin_series,
            "monthly_precip": monthly_precip,
            "temp_anomaly": temp_anomaly,
            "heat_stress": heat_stress,
            "exploitation_systems": exploitation_systems,
            "meteo_observed": meteo_observed,
            "meteo_siar": meteo_siar,
            "irrigation_autonomy": irrigation_autonomy,
            "climate_by_province": climate_by_province,
            "meteo_forecast": meteo_forecast,
            "stress_evolution": stress_evolution,
            "reservoir_rows": reservoir_rows,
            "province_map_kpis": province_map_kpis,
            "weekly_deltas": weekly_deltas,
            "weekly_narrative": narrative,
            "alerts": alerts,
            "recommendations": recommendations,
            "risk_board": risk_board,
            "data_notes": [
                "Precipitación = avg_precipitation_mm (mm), no volumen de embalse.",
                "Déficit hídrico diario = ET0 − precip (mm); no es SPI-12.",
                "SPI-12 pendiente de serie climática de referencia en marts.",
                "Meteo observado = RIA diario; SiAR (MAPA) es capa complementaria de riego; pronóstico = AEMET (municipio) con fallback Open-Meteo.",
                "Autonomía de riego = piloto (embalse ÷ demanda SiAR×ha Junta 2023); no es un modelo de derechos.",
            ],
        }
