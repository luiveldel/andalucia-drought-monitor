"""Irrigation autonomy: reservoir storage vs SiAR net demand (ET0 − Pe).

Piloto afinado:
- Excluye sistemas de explotación claramente urbanos (ABASTECIMIENTO …).
- Kc provincial según cultivo dominante (aproximación documental).
- Déficit acumulado 7d/30d, burn rate de embalse y tendencia de autonomía.
No es un modelo de derechos ni de asignación real de caudales.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

# Junta de Andalucía / AGAPA — tipología de regadío 2023 (ha).
IRRIGATED_HA_2023: dict[str, int] = {
    "Almería": 37_276,
    "Cádiz": 44_420,
    "Córdoba": 117_533,
    "Granada": 152_638,
    "Huelva": 34_518,
    "Jaén": 321_640,
    "Málaga": 72_690,
    "Sevilla": 215_377,
}

# Kc provincial aproximado por cartera dominante (olivar, hortícola, berries…).
# Referencia FAO-56 / práctica andaluza; no sustituye un balance por zona regable.
KC_BY_PROVINCE: dict[str, float] = {
    "Almería": 0.95,  # invernadero hortícola intensivo
    "Cádiz": 0.80,
    "Córdoba": 0.70,  # olivar + extensivos
    "Granada": 0.75,
    "Huelva": 0.90,  # berries / fresa
    "Jaén": 0.65,  # olivar dominante
    "Málaga": 0.75,
    "Sevilla": 0.85,  # arroz, algodón, olivar
}

DEFAULT_KC = 0.75

# Sistemas de explotación claramente urbanos en el catálogo REDIAM.
URBAN_SUPPLY_SYSTEMS = {
    "ABASTECIMIENTO DE SEVILLA",
    "ABASTECIMIENTO DE JAÉN",
}

# 1 mm over 1 ha = 10 m³ = 1e-5 hm³
MM_HA_TO_HM3 = 1e-5

URBAN_SQL_IN = "'ABASTECIMIENTO DE SEVILLA', 'ABASTECIMIENTO DE JAÉN'"


def _f(v: Any, nd: int = 2) -> float | None:
    if v is None:
        return None
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


def _rows(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params)
    return [dict(row._mapping) for row in result]


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _daily_demand_hm3(et0_mm: float, pe_mm: float, irrigated_ha: int, kc: float) -> float:
    """Spot demand used for days_autonomy: max(0, ET0×Kc − Pe) × ha × 1e-5."""
    net_mm = max(0.0, float(et0_mm) * kc - float(pe_mm))
    return net_mm * irrigated_ha * MM_HA_TO_HM3


def _deficit_day_hm3(et0_mm: float, pe_mm: float, irrigated_ha: int, kc: float) -> float:
    """Accumulated-deficit day: Kc × max(0, ET0 − Pe) × ha × 1e-5."""
    net_mm = kc * max(0.0, float(et0_mm) - float(pe_mm))
    return net_mm * irrigated_ha * MM_HA_TO_HM3


def _empty() -> dict[str, Any]:
    return {
        "available": False,
        "as_of_reservoir": None,
        "as_of_siar": None,
        "kc": None,
        "irrigated_ha_source": "Junta Andalucía tipología regadío 2023 (estático)",
        "storage_scope": (
            "Volumen provincial excluyendo sistemas ABASTECIMIENTO DE SEVILLA "
            "y ABASTECIMIENTO DE JAÉN. El resto sigue siendo multipropósito."
        ),
        "note": "",
        "regional": None,
        "by_province": [],
        "method_es": (
            "Días de autonomía ≈ volumen embalsado (sin sistemas urbanos explícitos) "
            "÷ demanda diaria (Kc_provincial × max(0, ET0_SiAR − Pe_SiAR) mm × ha × 1e-5). "
            "Déficit 7d/30d = suma de Kc×max(0,ET0−Pe)×ha×1e-5. "
            "Burn rate = Δembalsado usable / Δdías entre las dos últimas fechas de embalse. "
            "Kc por cultivo dominante; ha Junta 2023."
        ),
    }


def _risk_level(days: float | None) -> str:
    if days is None:
        return "unknown"
    if days < 30:
        return "critical"
    if days < 60:
        return "warning"
    if days < 120:
        return "watch"
    return "ok"


def _pack_province(
    *,
    province: str,
    stored_hm3: float,
    stored_gross_hm3: float,
    capacity_hm3: float,
    fill_pct: float | None,
    et0_mm: float,
    pe_mm: float,
    precip_mm: float,
    station_count: int,
    irrigated_ha: int,
    kc: float,
    urban_excluded_hm3: float,
    deficit_7d_hm3: float | None = None,
    deficit_30d_hm3: float | None = None,
    storage_burn_hm3_per_day: float | None = None,
    burn_vs_demand_ratio: float | None = None,
    autonomy_trend: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    demand_hm3 = _daily_demand_hm3(et0_mm, pe_mm, irrigated_ha, kc)
    net_mm = max(0.0, float(et0_mm) * kc - float(pe_mm))
    days = (stored_hm3 / demand_hm3) if demand_hm3 > 1e-9 else None
    weeks = (days / 7.0) if days is not None else None
    days_gross = (
        (stored_gross_hm3 / demand_hm3) if demand_hm3 > 1e-9 else None
    )

    return {
        "province_name": province,
        "stored_hm3": _f(stored_hm3, 1),
        "stored_gross_hm3": _f(stored_gross_hm3, 1),
        "urban_excluded_hm3": _f(urban_excluded_hm3, 1),
        "capacity_hm3": _f(capacity_hm3, 1),
        "fill_pct": _f(fill_pct, 1),
        "irrigated_ha": irrigated_ha,
        "kc": _f(kc, 2),
        "et0_mm": _f(et0_mm, 2),
        "pe_mm": _f(pe_mm, 2),
        "precip_mm": _f(precip_mm, 2),
        "net_demand_mm": _f(net_mm, 2),
        "daily_demand_hm3": _f(demand_hm3, 3),
        "days_autonomy": _f(days, 1) if days is not None else None,
        "days_autonomy_gross": _f(days_gross, 1) if days_gross is not None else None,
        "weeks_autonomy": _f(weeks, 1) if weeks is not None else None,
        "risk_level": _risk_level(days),
        "siar_station_count": station_count,
        "deficit_7d_hm3": _f(deficit_7d_hm3, 3) if deficit_7d_hm3 is not None else None,
        "deficit_30d_hm3": _f(deficit_30d_hm3, 3) if deficit_30d_hm3 is not None else None,
        "storage_burn_hm3_per_day": (
            _f(storage_burn_hm3_per_day, 3)
            if storage_burn_hm3_per_day is not None
            else None
        ),
        "burn_vs_demand_ratio": (
            _f(burn_vs_demand_ratio, 2) if burn_vs_demand_ratio is not None else None
        ),
        "autonomy_trend": autonomy_trend or [],
    }


def _load_siar_history(
    conn: Connection, as_of_siar: str, days: int = 30
) -> dict[str, list[dict[str, Any]]]:
    """province -> list of {date, et0_mm, pe_mm, precip_mm, station_count} newest last."""
    rows = _rows(
        conn,
        """
        SELECT
            fecha::text AS d,
            provincia_nombre AS province_name,
            COUNT(*)::int AS station_count,
            AVG(et0)::float AS et0_mm,
            AVG(COALESCE(precip_efectiva, 0))::float AS pe_mm,
            AVG(COALESCE(precipitacion, 0))::float AS precip_mm
        FROM raw.raw_siar_clima_diario
        WHERE ccaa_codigo = 'AND'
          AND fecha <= CAST(:d AS date)
          AND fecha > CAST(:d AS date) - :n
          AND provincia_nombre IS NOT NULL
          AND et0 IS NOT NULL
        GROUP BY fecha, provincia_nombre
        ORDER BY fecha ASC
        """,
        d=as_of_siar,
        n=days,
    )
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        out[str(r["province_name"])].append(
            {
                "date": str(r["d"])[:10],
                "et0_mm": float(r["et0_mm"] or 0),
                "pe_mm": float(r.get("pe_mm") or 0),
                "precip_mm": float(r.get("precip_mm") or 0),
                "station_count": int(r.get("station_count") or 0),
            }
        )
    return out


def _load_storage_history(
    conn: Connection, as_of_res: str, lookback_days: int = 60
) -> dict[str, list[dict[str, Any]]]:
    """province -> list of {date, stored_hm3, stored_gross_hm3, ...} ascending."""
    rows = _rows(
        conn,
        f"""
        SELECT
            f.observation_date::text AS d,
            r.province_name,
            SUM(f.stored_volume_hm3)::float AS stored_gross_hm3,
            SUM(f.reservoir_capacity_hm3)::float AS capacity_gross_hm3,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN ({URBAN_SQL_IN})
                    THEN 0.0
                    ELSE f.stored_volume_hm3
                END
            )::float AS stored_hm3,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN ({URBAN_SQL_IN})
                    THEN 0.0
                    ELSE f.reservoir_capacity_hm3
                END
            )::float AS capacity_hm3,
            SUM(
                CASE
                    WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN ({URBAN_SQL_IN})
                    THEN f.stored_volume_hm3
                    ELSE 0.0
                END
            )::float AS urban_excluded_hm3
        FROM marts.fact_reservoir_daily f
        JOIN marts.dim_reservoirs r ON r.reservoir_key = f.reservoir_key
        WHERE f.observation_date <= CAST(:d AS date)
          AND f.observation_date > CAST(:d AS date) - :n
          AND r.province_name IS NOT NULL
        GROUP BY f.observation_date, r.province_name
        ORDER BY f.observation_date ASC
        """,
        d=as_of_res,
        n=lookback_days,
    )
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        out[str(r["province_name"])].append(
            {
                "date": str(r["d"])[:10],
                "stored_hm3": float(r["stored_hm3"] or 0),
                "stored_gross_hm3": float(r["stored_gross_hm3"] or 0),
                "capacity_hm3": float(r["capacity_hm3"] or 0),
                "urban_excluded_hm3": float(r.get("urban_excluded_hm3") or 0),
            }
        )
    return out


def _sum_deficit(
    siar_days: list[dict[str, Any]], irrigated_ha: int, kc: float, window: int
) -> float | None:
    if not siar_days:
        return None
    tail = siar_days[-window:]
    if not tail:
        return None
    return sum(
        _deficit_day_hm3(d["et0_mm"], d["pe_mm"], irrigated_ha, kc) for d in tail
    )


def _burn_rate(storage_days: list[dict[str, Any]]) -> float | None:
    """(stored_prev - stored_now) / delta_days using the two latest obs dates."""
    if len(storage_days) < 2:
        return None
    prev = storage_days[-2]
    now = storage_days[-1]
    d0 = _parse_date(prev["date"])
    d1 = _parse_date(now["date"])
    if not d0 or not d1:
        return None
    delta = (d1 - d0).days
    if delta <= 0:
        return None
    return (float(prev["stored_hm3"]) - float(now["stored_hm3"])) / float(delta)


def _autonomy_trend(
    *,
    siar_days: list[dict[str, Any]],
    storage_days: list[dict[str, Any]],
    irrigated_ha: int,
    kc: float,
    max_points: int = 14,
) -> list[dict[str, Any]]:
    storage_by = {s["date"]: s for s in storage_days}
    points: list[dict[str, Any]] = []
    for s in siar_days:
        st = storage_by.get(s["date"])
        if not st:
            continue
        demand = _daily_demand_hm3(s["et0_mm"], s["pe_mm"], irrigated_ha, kc)
        stored = float(st["stored_hm3"])
        days = (stored / demand) if demand > 1e-9 else None
        points.append(
            {
                "date": s["date"],
                "days_autonomy": _f(days, 1) if days is not None else None,
                "stored_hm3": _f(stored, 1),
                "daily_demand_hm3": _f(demand, 3),
            }
        )
    if len(points) > max_points:
        points = points[-max_points:]
    return points


def load_irrigation_autonomy(conn: Connection) -> dict[str, Any]:
    empty = _empty()
    try:
        res_asof = _rows(
            conn,
            "SELECT MAX(observation_date)::text AS d FROM marts.fact_reservoir_daily",
        )
        siar_asof = _rows(
            conn,
            "SELECT MAX(fecha)::text AS d FROM raw.raw_siar_clima_diario WHERE ccaa_codigo = 'AND'",
        )
        as_of_res = (res_asof[0].get("d") if res_asof else None) or None
        as_of_siar = (siar_asof[0].get("d") if siar_asof else None) or None
        if not as_of_res or not as_of_siar:
            empty["note"] = "Faltan datos de embalses o SiAR para el cálculo."
            return empty

        as_of_res = str(as_of_res)[:10]
        as_of_siar = str(as_of_siar)[:10]

        storage = _rows(
            conn,
            f"""
            SELECT
                r.province_name,
                SUM(f.stored_volume_hm3)::float AS stored_gross_hm3,
                SUM(f.reservoir_capacity_hm3)::float AS capacity_gross_hm3,
                AVG(f.fill_percentage)::float AS fill_pct_gross,
                SUM(
                    CASE
                        WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN ({URBAN_SQL_IN})
                        THEN 0.0
                        ELSE f.stored_volume_hm3
                    END
                )::float AS stored_hm3,
                SUM(
                    CASE
                        WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN ({URBAN_SQL_IN})
                        THEN 0.0
                        ELSE f.reservoir_capacity_hm3
                    END
                )::float AS capacity_hm3,
                SUM(
                    CASE
                        WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN ({URBAN_SQL_IN})
                        THEN f.stored_volume_hm3
                        ELSE 0.0
                    END
                )::float AS urban_excluded_hm3
            FROM marts.fact_reservoir_daily f
            JOIN marts.dim_reservoirs r ON r.reservoir_key = f.reservoir_key
            WHERE f.observation_date = CAST(:d AS date)
              AND r.province_name IS NOT NULL
            GROUP BY r.province_name
            """,
            d=as_of_res,
        )
        storage_by = {str(r["province_name"]): r for r in storage}

        siar = _rows(
            conn,
            """
            SELECT
                provincia_nombre AS province_name,
                COUNT(*)::int AS station_count,
                AVG(et0)::float AS et0_mm,
                AVG(COALESCE(precip_efectiva, 0))::float AS pe_mm,
                AVG(COALESCE(precipitacion, 0))::float AS precip_mm
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND'
              AND fecha = CAST(:d AS date)
              AND provincia_nombre IS NOT NULL
            GROUP BY provincia_nombre
            """,
            d=as_of_siar,
        )
        siar_by = {str(r["province_name"]): r for r in siar}

        siar_hist = _load_siar_history(conn, as_of_siar, days=30)
        storage_hist = _load_storage_history(conn, as_of_res, lookback_days=60)

        by_province: list[dict[str, Any]] = []
        for province, ha in IRRIGATED_HA_2023.items():
            st = storage_by.get(province)
            sm = siar_by.get(province)
            if not st or not sm or sm.get("et0_mm") is None:
                continue
            kc = KC_BY_PROVINCE.get(province, DEFAULT_KC)
            sh = siar_hist.get(province, [])
            rh = storage_hist.get(province, [])
            demand = _daily_demand_hm3(
                float(sm["et0_mm"]),
                float(sm.get("pe_mm") or 0),
                ha,
                kc,
            )
            burn = _burn_rate(rh)
            ratio = None
            if burn is not None and demand > 1e-9:
                ratio = burn / demand
            by_province.append(
                _pack_province(
                    province=province,
                    stored_hm3=float(st["stored_hm3"] or 0),
                    stored_gross_hm3=float(st["stored_gross_hm3"] or 0),
                    capacity_hm3=float(st["capacity_hm3"] or 0),
                    fill_pct=(
                        (100.0 * float(st["stored_hm3"] or 0) / float(st["capacity_hm3"]))
                        if st.get("capacity_hm3")
                        else st.get("fill_pct_gross")
                    ),
                    et0_mm=float(sm["et0_mm"]),
                    pe_mm=float(sm.get("pe_mm") or 0),
                    precip_mm=float(sm.get("precip_mm") or 0),
                    station_count=int(sm.get("station_count") or 0),
                    irrigated_ha=ha,
                    kc=kc,
                    urban_excluded_hm3=float(st.get("urban_excluded_hm3") or 0),
                    deficit_7d_hm3=_sum_deficit(sh, ha, kc, 7),
                    deficit_30d_hm3=_sum_deficit(sh, ha, kc, 30),
                    storage_burn_hm3_per_day=burn,
                    burn_vs_demand_ratio=ratio,
                    autonomy_trend=_autonomy_trend(
                        siar_days=sh, storage_days=rh, irrigated_ha=ha, kc=kc
                    ),
                )
            )

        by_province.sort(
            key=lambda r: (r["days_autonomy"] is None, r["days_autonomy"] or 0)
        )

        if by_province:
            stored = sum(float(p["stored_hm3"] or 0) for p in by_province)
            stored_gross = sum(float(p["stored_gross_hm3"] or 0) for p in by_province)
            urban_ex = sum(float(p["urban_excluded_hm3"] or 0) for p in by_province)
            capacity = sum(float(p["capacity_hm3"] or 0) for p in by_province)
            ha = sum(int(p["irrigated_ha"] or 0) for p in by_province)
            demand = sum(float(p["daily_demand_hm3"] or 0) for p in by_province)
            et0 = sum(
                float(p["et0_mm"] or 0) * int(p["irrigated_ha"] or 0) for p in by_province
            ) / ha
            pe = sum(
                float(p["pe_mm"] or 0) * int(p["irrigated_ha"] or 0) for p in by_province
            ) / ha
            precip = sum(
                float(p["precip_mm"] or 0) * int(p["irrigated_ha"] or 0)
                for p in by_province
            ) / ha
            kc_reg = sum(
                float(p["kc"] or DEFAULT_KC) * int(p["irrigated_ha"] or 0)
                for p in by_province
            ) / ha
            stations = sum(int(p["siar_station_count"] or 0) for p in by_province)
            fill = (100.0 * stored / capacity) if capacity else None

            # Regional deficit / burn: sum of province components
            def7 = sum(float(p["deficit_7d_hm3"] or 0) for p in by_province)
            def30 = sum(float(p["deficit_30d_hm3"] or 0) for p in by_province)
            burns = [
                float(p["storage_burn_hm3_per_day"])
                for p in by_province
                if p.get("storage_burn_hm3_per_day") is not None
            ]
            burn_reg = sum(burns) if burns else None
            ratio_reg = (burn_reg / demand) if (burn_reg is not None and demand > 1e-9) else None

            # Regional trend: dates with SiAR+embalse for every packed province
            packed_names = [p["province_name"] for p in by_province]
            all_siar_dates = set()
            for name in packed_names:
                for d in siar_hist.get(name, []):
                    all_siar_dates.add(d["date"])
            all_res_dates = set()
            for name in packed_names:
                for d in storage_hist.get(name, []):
                    all_res_dates.add(d["date"])
            common = sorted(all_siar_dates & all_res_dates)[-14:]
            regional_trend: list[dict[str, Any]] = []
            for d in common:
                stored_d = 0.0
                demand_d = 0.0
                complete = True
                for province in packed_names:
                    ha_p = IRRIGATED_HA_2023[province]
                    kc_p = KC_BY_PROVINCE.get(province, DEFAULT_KC)
                    st_list = {x["date"]: x for x in storage_hist.get(province, [])}
                    sm_list = {x["date"]: x for x in siar_hist.get(province, [])}
                    st_d = st_list.get(d)
                    sm_d = sm_list.get(d)
                    if not st_d or not sm_d:
                        complete = False
                        break
                    stored_d += float(st_d["stored_hm3"])
                    demand_d += _daily_demand_hm3(
                        sm_d["et0_mm"], sm_d["pe_mm"], ha_p, kc_p
                    )
                if not complete or demand_d <= 1e-9:
                    continue
                days_d = stored_d / demand_d
                regional_trend.append(
                    {
                        "date": d,
                        "days_autonomy": _f(days_d, 1),
                        "stored_hm3": _f(stored_d, 1),
                        "daily_demand_hm3": _f(demand_d, 3),
                    }
                )

            regional = _pack_province(
                province="Andalucía",
                stored_hm3=stored,
                stored_gross_hm3=stored_gross,
                capacity_hm3=capacity,
                fill_pct=fill,
                et0_mm=et0,
                pe_mm=pe,
                precip_mm=precip,
                station_count=stations,
                irrigated_ha=ha,
                kc=kc_reg,
                urban_excluded_hm3=urban_ex,
                deficit_7d_hm3=def7,
                deficit_30d_hm3=def30,
                storage_burn_hm3_per_day=burn_reg,
                burn_vs_demand_ratio=ratio_reg,
                autonomy_trend=regional_trend,
            )
            if demand > 1e-9:
                regional["daily_demand_hm3"] = _f(demand, 3)
                days = stored / demand
                regional["days_autonomy"] = _f(days, 1)
                regional["weeks_autonomy"] = _f(days / 7.0, 1)
                regional["risk_level"] = _risk_level(days)
                regional["days_autonomy_gross"] = _f(stored_gross / demand, 1)
        else:
            regional = None

        return {
            "available": bool(by_province),
            "as_of_reservoir": as_of_res,
            "as_of_siar": as_of_siar,
            "kc": None,
            "irrigated_ha_source": empty["irrigated_ha_source"],
            "storage_scope": empty["storage_scope"],
            "method_es": empty["method_es"],
            "note": (
                "Piloto afinado. Ha Junta 2023; Kc por cultivo dominante; "
                "excluídos sistemas urbanos explícitos (ABASTECIMIENTO Sevilla/Jaén). "
                "Déficit 7d/30d y burn rate usan historial SiAR/embalses disponible. "
                "El resto de embalses sigue siendo multipropósito."
            ),
            "regional": regional,
            "by_province": by_province,
        }
    except Exception as exc:  # noqa: BLE001
        empty["note"] = f"Error calculando autonomía de riego: {exc}"
        return empty
