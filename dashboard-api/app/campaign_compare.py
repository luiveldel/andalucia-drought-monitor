"""Interannual agricultural-campaign comparison (Apr–Sep) for irrigation demand.

Compares cumulative net demand for the same campaign window across years:
  demanda_día = Kc × max(0, ET0 − Pe) × ha × 1e-5  (hm³)
  acumulado   = suma desde 1 abr hasta el mismo día-del-año de referencia
                (o 30 sep si la campaña ya cerró).

Prefers SiAR daily means; when a year lacks enough SiAR days, falls back to
RIA ET0 with Pe ≈ precip bruta, always labelled as proxy.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy.engine import Connection

from app.irrigation_autonomy import (
    DEFAULT_KC,
    IRRIGATED_HA_2023,
    KC_BY_PROVINCE,
    _deficit_day_hm3,
    _f,
    _parse_date,
    _rows,
)

CAMPAIGN_START_MONTH = 4
CAMPAIGN_START_DAY = 1
CAMPAIGN_END_MONTH = 9
CAMPAIGN_END_DAY = 30
MIN_DAYS = 14
SIAR_PREFER_DAYS = 20
LOOKBACK_YEARS = 5


def _empty() -> dict[str, Any]:
    return {
        "available": False,
        "campaign": {
            "label_es": "Campaña agrícola abr–sep",
            "start_month": CAMPAIGN_START_MONTH,
            "start_day": CAMPAIGN_START_DAY,
            "end_month": CAMPAIGN_END_MONTH,
            "end_day": CAMPAIGN_END_DAY,
        },
        "as_of": None,
        "through_doy": None,
        "current_year": None,
        "unit_demand": "hm3",
        "unit_depth": "mm",
        "formula_es": (
            "demanda_día = Kc_provincial × max(0, ET0 − Pe) × ha × 1e-5 hm³; "
            "acumulado = suma desde 1 abr hasta el mismo día del año (o 30 sep)."
        ),
        "note_es": "",
        "caveats_es": [],
        "method_es": "",
        "coverage": {
            "siar_years": [],
            "ria_proxy_years": [],
            "siar_min_fecha": None,
            "siar_max_fecha": None,
            "ria_min_fecha": None,
            "ria_max_fecha": None,
        },
        "headline_es": "",
        "headline_en": "",
        "regional": None,
        "by_province": [],
        "years": [],
        "comparisons": [],
    }


def _caveats(*, used_ria: bool, siar_thin: bool) -> list[str]:
    out = [
        "Ventana de campaña: 1 abr – 30 sep (o hasta el último día disponible del año en curso).",
        "La comparación usa el mismo tramo calendario (mismo día del año) en todos los años.",
        "Ha de regadío: tipología Junta 2023 (estático). Kc provincial por cultivo dominante.",
        "No es un balance de derechos ni dotaciones oficiales.",
    ]
    if siar_thin:
        out.append(
            "El historial SiAR en raw es corto (principalmente el año en curso / backfill "
            "de verano). Los años sin SiAR suficiente usan RIA como proxy etiquetado."
        )
    if used_ria:
        out.append(
            "Proxy RIA: ET0 y precipitación bruta de raw.raw_ria_clima_diario "
            "(RIA no publica PePMon; Pe ≈ precip bruta). Comparar con cautela frente a SiAR."
        )
    out.append(
        f"Si un año tiene menos de {MIN_DAYS} días con dato en la ventana, se omite."
    )
    return out


def _safe_through(year: int, as_of: date) -> date:
    """Same month/day as as_of in `year`, capped to campaign end."""
    end = date(year, CAMPAIGN_END_MONTH, CAMPAIGN_END_DAY)
    start = date(year, CAMPAIGN_START_MONTH, CAMPAIGN_START_DAY)
    try:
        through = date(year, as_of.month, as_of.day)
    except ValueError:
        through = date(year, as_of.month, 28)
    if through > end:
        through = end
    if through < start:
        return start - timedelta(days=1)
    return through


def _verdict(delta_pct: float | None) -> str:
    if delta_pct is None:
        return "unknown"
    if delta_pct >= 5.0:
        return "worse"
    if delta_pct <= -5.0:
        return "better"
    return "similar"


def _plain_es(year: int, verdict: str, delta_pct: float | None) -> str:
    if delta_pct is None:
        return f"Sin dato comparable frente a {year}."
    sign = "+" if delta_pct >= 0 else ""
    if verdict == "worse":
        return f"Vamos peor que {year} en demanda acumulada ({sign}{delta_pct:.0f}%)."
    if verdict == "better":
        return f"Vamos mejor que {year} en demanda acumulada ({sign}{delta_pct:.0f}%)."
    return f"Estamos parecidos a {year} en demanda acumulada ({sign}{delta_pct:.0f}%)."


def _plain_en(year: int, verdict: str, delta_pct: float | None) -> str:
    if delta_pct is None:
        return f"No comparable figure vs {year}."
    sign = "+" if delta_pct >= 0 else ""
    if verdict == "worse":
        return f"We are worse than {year} on cumulative demand ({sign}{delta_pct:.0f}%)."
    if verdict == "better":
        return f"We are better than {year} on cumulative demand ({sign}{delta_pct:.0f}%)."
    return f"We are similar to {year} on cumulative demand ({sign}{delta_pct:.0f}%)."


def _coverage_meta(conn: Connection) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "siar_years": [],
        "ria_proxy_years": [],
        "siar_min_fecha": None,
        "siar_max_fecha": None,
        "ria_min_fecha": None,
        "ria_max_fecha": None,
    }
    try:
        siar = _rows(
            conn,
            """
            SELECT MIN(fecha)::text AS mn, MAX(fecha)::text AS mx
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND' AND et0 IS NOT NULL
            """,
        )
        if siar:
            meta["siar_min_fecha"] = siar[0].get("mn")
            meta["siar_max_fecha"] = siar[0].get("mx")
    except Exception:  # noqa: BLE001
        pass
    try:
        ria = _rows(
            conn,
            """
            SELECT MIN(fecha)::text AS mn, MAX(fecha)::text AS mx
            FROM raw.raw_ria_clima_diario
            WHERE et0 IS NOT NULL
            """,
        )
        if ria:
            meta["ria_min_fecha"] = ria[0].get("mn")
            meta["ria_max_fecha"] = ria[0].get("mx")
    except Exception:  # noqa: BLE001
        pass
    return meta


def _count_days(conn: Connection, source: str, start: date, end: date) -> int:
    if end < start:
        return 0
    if source == "siar":
        rows = _rows(
            conn,
            """
            SELECT COUNT(DISTINCT fecha)::int AS n
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND'
              AND fecha >= CAST(:start AS date)
              AND fecha <= CAST(:end AS date)
              AND et0 IS NOT NULL
            """,
            start=start.isoformat(),
            end=end.isoformat(),
        )
    else:
        rows = _rows(
            conn,
            """
            SELECT COUNT(DISTINCT fecha)::int AS n
            FROM raw.raw_ria_clima_diario
            WHERE fecha >= CAST(:start AS date)
              AND fecha <= CAST(:end AS date)
              AND et0 IS NOT NULL
            """,
            start=start.isoformat(),
            end=end.isoformat(),
        )
    return int(rows[0]["n"]) if rows else 0


def _load_daily_means(
    conn: Connection,
    *,
    source: str,
    start: date,
    end: date,
) -> dict[str, list[dict[str, Any]]]:
    """province -> list of {date, et0_mm, pe_mm, precip_mm, station_count}."""
    if source == "siar":
        rows = _rows(
            conn,
            """
            SELECT
                fecha::text AS d,
                provincia_nombre AS province_name,
                COUNT(*)::int AS station_count,
                AVG(et0)::float AS et0_mm,
                AVG(COALESCE(precip_efectiva, precipitacion, 0))::float AS pe_mm,
                AVG(COALESCE(precipitacion, 0))::float AS precip_mm
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND'
              AND fecha >= CAST(:start AS date)
              AND fecha <= CAST(:end AS date)
              AND provincia_nombre IS NOT NULL
              AND et0 IS NOT NULL
            GROUP BY fecha, provincia_nombre
            ORDER BY fecha ASC
            """,
            start=start.isoformat(),
            end=end.isoformat(),
        )
    else:
        rows = _rows(
            conn,
            """
            SELECT
                fecha::text AS d,
                provincia_nombre AS province_name,
                COUNT(*)::int AS station_count,
                AVG(et0)::float AS et0_mm,
                AVG(COALESCE(precipitacion, 0))::float AS pe_mm,
                AVG(COALESCE(precipitacion, 0))::float AS precip_mm
            FROM raw.raw_ria_clima_diario
            WHERE fecha >= CAST(:start AS date)
              AND fecha <= CAST(:end AS date)
              AND provincia_nombre IS NOT NULL
              AND et0 IS NOT NULL
            GROUP BY fecha, provincia_nombre
            ORDER BY fecha ASC
            """,
            start=start.isoformat(),
            end=end.isoformat(),
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


def _accumulate(
    daily_by_prov: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    by_province: list[dict[str, Any]] = []
    all_dates: set[str] = set()
    total_hm3 = 0.0
    total_ha = 0

    for province, days in sorted(daily_by_prov.items()):
        if province not in IRRIGATED_HA_2023:
            continue
        ha = int(IRRIGATED_HA_2023[province])
        kc = float(KC_BY_PROVINCE.get(province, DEFAULT_KC))
        if not days:
            continue
        demand_hm3 = 0.0
        et0_sum = 0.0
        pe_sum = 0.0
        net_mm_sum = 0.0
        for d in days:
            all_dates.add(d["date"])
            demand_hm3 += _deficit_day_hm3(d["et0_mm"], d["pe_mm"], ha, kc)
            et0_sum += float(d["et0_mm"])
            pe_sum += float(d["pe_mm"])
            net_mm_sum += kc * max(0.0, float(d["et0_mm"]) - float(d["pe_mm"]))
        by_province.append(
            {
                "province_name": province,
                "irrigated_ha": ha,
                "kc": _f(kc, 2),
                "days_with_data": len(days),
                "cum_et0_mm": _f(et0_sum, 1),
                "cum_pe_mm": _f(pe_sum, 1),
                "cum_net_demand_mm": _f(net_mm_sum, 1),
                "cum_demand_hm3": _f(demand_hm3, 2),
            }
        )
        total_hm3 += demand_hm3
        total_ha += ha

    weighted_net = 0.0
    weighted_et0 = 0.0
    weighted_pe = 0.0
    w = 0
    for p in by_province:
        ha = int(p["irrigated_ha"] or 0)
        weighted_net += float(p["cum_net_demand_mm"] or 0) * ha
        weighted_et0 += float(p["cum_et0_mm"] or 0) * ha
        weighted_pe += float(p["cum_pe_mm"] or 0) * ha
        w += ha

    regional = {
        "province_name": "Andalucía",
        "irrigated_ha": total_ha,
        "days_with_data": len(all_dates),
        "cum_et0_mm": _f(weighted_et0 / w, 1) if w else None,
        "cum_pe_mm": _f(weighted_pe / w, 1) if w else None,
        "cum_net_demand_mm": _f(weighted_net / w, 1) if w else None,
        "cum_demand_hm3": _f(total_hm3, 2),
    }
    by_province.sort(key=lambda r: float(r.get("cum_demand_hm3") or 0), reverse=True)
    return regional, by_province, len(all_dates)


def build_campaign_compare(
    conn: Connection,
    *,
    as_of: str | date | None = None,
) -> dict[str, Any]:
    """Build Apr–Sep cumulative demand comparison across available years."""
    out = _empty()
    try:
        if as_of is None:
            latest = _rows(
                conn,
                """
                SELECT GREATEST(
                    COALESCE(
                        (SELECT MAX(fecha) FROM raw.raw_siar_clima_diario
                         WHERE ccaa_codigo='AND'),
                        DATE '1900-01-01'
                    ),
                    COALESCE(
                        (SELECT MAX(fecha) FROM raw.raw_ria_clima_diario),
                        DATE '1900-01-01'
                    )
                )::text AS d
                """,
            )
            as_of_s = latest[0]["d"] if latest else None
            if not as_of_s or str(as_of_s).startswith("1900"):
                out["note_es"] = "Sin fechas SiAR/RIA para anclar la campaña."
                out["caveats_es"] = _caveats(used_ria=False, siar_thin=True)
                return out
            as_of_d = _parse_date(as_of_s)
        else:
            as_of_d = _parse_date(as_of) if not isinstance(as_of, date) else as_of
        if not as_of_d:
            out["note_es"] = "Fecha de referencia no válida."
            return out

        current_year = as_of_d.year
        campaign_started = (as_of_d.month, as_of_d.day) >= (
            CAMPAIGN_START_MONTH,
            CAMPAIGN_START_DAY,
        )
        ref_for_doy = as_of_d
        camp_end = date(current_year, CAMPAIGN_END_MONTH, CAMPAIGN_END_DAY)
        if ref_for_doy > camp_end:
            ref_for_doy = camp_end
        if not campaign_started:
            ref_for_doy = date(current_year, CAMPAIGN_START_MONTH, CAMPAIGN_START_DAY)

        coverage = _coverage_meta(conn)
        out["as_of"] = as_of_d.isoformat()
        out["current_year"] = current_year
        out["through_doy"] = {
            "month": ref_for_doy.month,
            "day": ref_for_doy.day,
            "label": f"{ref_for_doy.day:02d}/{ref_for_doy.month:02d}",
        }

        years_out: list[dict[str, Any]] = []
        used_ria = False
        siar_years_used: list[int] = []
        ria_years_used: list[int] = []

        for y in range(current_year - LOOKBACK_YEARS, current_year + 1):
            start = date(y, CAMPAIGN_START_MONTH, CAMPAIGN_START_DAY)
            through = _safe_through(y, ref_for_doy)
            if through < start:
                continue
            if y == current_year and not campaign_started:
                continue

            n_siar = _count_days(conn, "siar", start, through)
            n_ria = _count_days(conn, "ria", start, through)

            source: str | None = None
            source_label = ""
            if n_siar >= SIAR_PREFER_DAYS or (n_siar >= MIN_DAYS and n_siar >= n_ria):
                source = "siar"
                source_label = "SiAR (MAPA)"
            elif n_ria >= MIN_DAYS:
                source = "ria_proxy"
                source_label = "RIA (proxy ET0×Kc; Pe≈precip)"
                used_ria = True
            elif n_siar >= MIN_DAYS:
                source = "siar"
                source_label = "SiAR (MAPA, cobertura parcial)"
            else:
                continue

            daily = _load_daily_means(
                conn,
                source="siar" if source == "siar" else "ria",
                start=start,
                end=through,
            )
            regional, by_prov, n_days = _accumulate(daily)
            if n_days < MIN_DAYS or not by_prov:
                continue

            if source == "siar":
                siar_years_used.append(y)
            else:
                ria_years_used.append(y)

            years_out.append(
                {
                    "year": y,
                    "source": source,
                    "source_label_es": source_label,
                    "window_start": start.isoformat(),
                    "window_end": through.isoformat(),
                    "days_with_data": n_days,
                    "days_siar": n_siar,
                    "days_ria": n_ria,
                    "is_current": y == current_year,
                    "regional": regional,
                    "by_province": by_prov,
                }
            )

        coverage["siar_years"] = siar_years_used
        coverage["ria_proxy_years"] = ria_years_used
        out["coverage"] = coverage

        siar_thin = len(siar_years_used) <= 1
        out["caveats_es"] = _caveats(used_ria=used_ria, siar_thin=siar_thin)
        out["method_es"] = (
            "Para cada año se acumula la demanda neta provincial "
            "(Kc×max(0,ET0−Pe)×ha×1e-5) desde el 1 de abril hasta el mismo "
            f"día del año que la referencia ({ref_for_doy.day:02d}/{ref_for_doy.month:02d}), "
            "o hasta el 30 de septiembre si la campaña ya cerró. "
            "Se prefiere SiAR; si un año no tiene cobertura suficiente se usa RIA "
            "como proxy etiquetado. Δ% = (año_actual − año_ref) / año_ref × 100; "
            "positivo = más demanda (vamos peor)."
        )

        if not years_out:
            out["note_es"] = (
                "No hay años con cobertura mínima en la ventana abr–sep "
                f"(umbral {MIN_DAYS} días). Amplía el backfill SiAR/RIA."
            )
            return out

        out["years"] = [
            {
                "year": y["year"],
                "source": y["source"],
                "source_label_es": y["source_label_es"],
                "window_start": y["window_start"],
                "window_end": y["window_end"],
                "days_with_data": y["days_with_data"],
                "days_siar": y["days_siar"],
                "days_ria": y["days_ria"],
                "is_current": y["is_current"],
                "cum_demand_hm3": (y["regional"] or {}).get("cum_demand_hm3"),
                "cum_net_demand_mm": (y["regional"] or {}).get("cum_net_demand_mm"),
                "cum_et0_mm": (y["regional"] or {}).get("cum_et0_mm"),
                "cum_pe_mm": (y["regional"] or {}).get("cum_pe_mm"),
            }
            for y in years_out
        ]

        current = next((y for y in years_out if y["is_current"]), None)
        focus = current or years_out[-1]
        out["regional"] = {
            **(focus["regional"] or {}),
            "year": focus["year"],
            "source": focus["source"],
            "window_start": focus["window_start"],
            "window_end": focus["window_end"],
        }

        prov_years: dict[str, dict[int, float]] = defaultdict(dict)
        for y in years_out:
            for p in y["by_province"]:
                prov_years[p["province_name"]][y["year"]] = float(
                    p.get("cum_demand_hm3") or 0
                )
        by_province_out: list[dict[str, Any]] = []
        focus_by = {p["province_name"]: p for p in focus["by_province"]}
        for name, p in focus_by.items():
            series = [
                {"year": yy, "cum_demand_hm3": _f(prov_years[name].get(yy), 2)}
                for yy in sorted(prov_years[name])
            ]
            by_province_out.append(
                {
                    **p,
                    "year": focus["year"],
                    "source": focus["source"],
                    "series": series,
                }
            )
        out["by_province"] = by_province_out

        comparisons: list[dict[str, Any]] = []
        if current:
            cur_hm3 = float((current["regional"] or {}).get("cum_demand_hm3") or 0)
            for y in years_out:
                if y["is_current"]:
                    continue
                ref_hm3 = float((y["regional"] or {}).get("cum_demand_hm3") or 0)
                delta_hm3 = cur_hm3 - ref_hm3
                delta_pct = (
                    ((cur_hm3 - ref_hm3) / ref_hm3) * 100.0 if ref_hm3 > 1e-9 else None
                )
                delta_pct_r = _f(delta_pct, 1)
                verdict = _verdict(delta_pct_r)
                comparisons.append(
                    {
                        "vs_year": y["year"],
                        "vs_source": y["source"],
                        "current_hm3": _f(cur_hm3, 2),
                        "vs_hm3": _f(ref_hm3, 2),
                        "delta_hm3": _f(delta_hm3, 2),
                        "delta_pct": delta_pct_r,
                        "verdict": verdict,
                        "plain_es": _plain_es(y["year"], verdict, delta_pct_r),
                        "plain_en": _plain_en(y["year"], verdict, delta_pct_r),
                    }
                )
        out["comparisons"] = comparisons

        if comparisons:
            prefer = [2022, 2023, 2024, 2025]
            pick = None
            for py in prefer:
                pick = next((c for c in comparisons if c["vs_year"] == py), None)
                if pick:
                    break
            if not pick:
                pick = comparisons[0]
            out["headline_es"] = pick["plain_es"]
            out["headline_en"] = pick["plain_en"]
        elif current:
            out["headline_es"] = (
                f"Campaña {current_year}: demanda acumulada "
                f"{(current['regional'] or {}).get('cum_demand_hm3')} hm³ "
                f"(aún sin años previos comparables en la base)."
            )
            out["headline_en"] = (
                f"Campaign {current_year}: cumulative demand "
                f"{(current['regional'] or {}).get('cum_demand_hm3')} hm³ "
                f"(no prior comparable years in the database yet)."
            )
        else:
            out["headline_es"] = (
                "Hay historial de campañas previas, pero el año en curso aún no "
                "tiene datos suficientes en abr–sep."
            )
            out["headline_en"] = (
                "Prior campaign history exists, but the current year still lacks "
                "enough Apr–Sep data."
            )

        sources_note = []
        if siar_years_used:
            sources_note.append(
                "SiAR años: " + ", ".join(str(y) for y in siar_years_used)
            )
        if ria_years_used:
            sources_note.append(
                "RIA proxy años: " + ", ".join(str(y) for y in ria_years_used)
            )
        out["note_es"] = (
            f"Comparativa interanual abr–sep hasta "
            f"{ref_for_doy.day:02d}/{ref_for_doy.month:02d}. "
            + (" · ".join(sources_note) if sources_note else "")
        )
        out["available"] = True
        return out
    except Exception as exc:  # noqa: BLE001
        out["note_es"] = f"Error calculando comparativa de campaña: {exc}"
        out["caveats_es"] = _caveats(used_ria=False, siar_thin=True)
        return out
