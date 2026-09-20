"""Irrigation autonomy: reservoir storage vs SiAR net demand (ET0 − Pe).

Piloto afinado:
- Excluye sistemas de explotación claramente urbanos (ABASTECIMIENTO …).
- Kc provincial según cultivo dominante (aproximación documental).
No es un modelo de derechos ni de asignación real de caudales.
"""

from __future__ import annotations

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
) -> dict[str, Any]:
    net_mm = max(0.0, float(et0_mm) * kc - float(pe_mm))
    demand_hm3 = net_mm * irrigated_ha * MM_HA_TO_HM3
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
    }


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

        # Gross + irrigation-oriented storage in one pass
        storage = _rows(
            conn,
            """
            SELECT
                r.province_name,
                SUM(f.stored_volume_hm3)::float AS stored_gross_hm3,
                SUM(f.reservoir_capacity_hm3)::float AS capacity_gross_hm3,
                AVG(f.fill_percentage)::float AS fill_pct_gross,
                SUM(
                    CASE
                        WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN (
                            'ABASTECIMIENTO DE SEVILLA',
                            'ABASTECIMIENTO DE JAÉN'
                        )
                        THEN 0.0
                        ELSE f.stored_volume_hm3
                    END
                )::float AS stored_hm3,
                SUM(
                    CASE
                        WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN (
                            'ABASTECIMIENTO DE SEVILLA',
                            'ABASTECIMIENTO DE JAÉN'
                        )
                        THEN 0.0
                        ELSE f.reservoir_capacity_hm3
                    END
                )::float AS capacity_hm3,
                SUM(
                    CASE
                        WHEN UPPER(TRIM(COALESCE(r.exploitation_system, ''))) IN (
                            'ABASTECIMIENTO DE SEVILLA',
                            'ABASTECIMIENTO DE JAÉN'
                        )
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

        by_province: list[dict[str, Any]] = []
        for province, ha in IRRIGATED_HA_2023.items():
            st = storage_by.get(province)
            sm = siar_by.get(province)
            if not st or not sm or sm.get("et0_mm") is None:
                continue
            kc = KC_BY_PROVINCE.get(province, DEFAULT_KC)
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
            # demand-weighted regional kc / et0
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
            # effective regional kc from total demand identity
            # demand = kc_eff * et0 * ha * 1e-5 roughly; use ha-weighted mean kc
            kc_reg = sum(
                float(p["kc"] or DEFAULT_KC) * int(p["irrigated_ha"] or 0)
                for p in by_province
            ) / ha
            stations = sum(int(p["siar_station_count"] or 0) for p in by_province)
            fill = (100.0 * stored / capacity) if capacity else None
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
            )
            # sanity: regional days from aggregated demand
            if demand > 1e-9:
                regional["daily_demand_hm3"] = _f(demand, 3)
                days = stored / demand
                regional["days_autonomy"] = _f(days, 1)
                regional["weeks_autonomy"] = _f(days / 7.0, 1)
                regional["risk_level"] = _risk_level(days)
                if demand > 1e-9:
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
                "El resto de embalses sigue siendo multipropósito."
            ),
            "regional": regional,
            "by_province": by_province,
        }
    except Exception as exc:  # noqa: BLE001
        empty["note"] = f"Error calculando autonomía de riego: {exc}"
        return empty
