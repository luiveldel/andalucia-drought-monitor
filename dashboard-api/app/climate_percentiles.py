"""Multi-year SiAR (RIA fallback) ET0 / net-demand percentiles.

Flags whether the current year is extreme relative to available history.

Views
-----
same_doy
    Spot ET0 and net demand (Kc×max(0,ET0−Pe) mm) on the reference calendar
    day across years. Prefer SiAR; RIA proxy when a year lacks SiAR that day.
campaign_to_date
    Cumulative Apr–Sep (or through same DOY) ET0 / net demand / hm³ across
    years — same window as campaign_compare, with percentile ranks.

Never invents historical values. With 1–2 years of coverage still returns
current vs mean of available years and a clear low-confidence caveat.
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

LOOKBACK_YEARS = 8
CAMPAIGN_START_MONTH = 4
CAMPAIGN_START_DAY = 1
CAMPAIGN_END_MONTH = 9
CAMPAIGN_END_DAY = 30
MIN_CAMPAIGN_DAYS = 14
# When exact DOY has < this many prior-year samples, widen ± half-days (labelled).
DOY_WINDOW_EXPAND_IF_BELOW = 3
DOY_WINDOW_HALF_EXPANDED = 3
MIN_YEARS_OK = 3


def _empty() -> dict[str, Any]:
    return {
        "available": False,
        "as_of": None,
        "current_year": None,
        "through_doy": None,
        "unit_depth": "mm",
        "unit_demand": "hm3",
        "formula_es": (
            "demanda_neta_día (mm) = Kc_provincial × max(0, ET0 − Pe); "
            "demanda (hm³) = mm × ha × 1e-5. "
            "Percentil empírico entre años disponibles (mismo DOY o campaña hasta hoy)."
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
            "n_years_total": 0,
            "confidence": "none",
        },
        "headline_es": "",
        "headline_en": "",
        "regional": None,
        "by_province": [],
    }


def _caveats(*, used_ria: bool, thin: bool, doy_window: int) -> list[str]:
    out = [
        "Percentiles empíricos solo con años que tienen dato real; no se inventan valores.",
        "Mismo día del año (DOY) o misma ventana de campaña (1 abr → DOY de referencia).",
        "Ha de regadío: tipología Junta 2023 (estático). Kc provincial por cultivo dominante.",
        "Un percentil alto en ET0/demanda = año más extremo (más seco / más demanda).",
    ]
    if thin:
        out.append(
            "Historial corto (pocos años en raw). El percentil es orientativo; "
            "se muestra también el valor actual frente a la media de años disponibles."
        )
    if doy_window > 0:
        out.append(
            f"Ventana DOY ampliada a ±{doy_window} días porque había pocos años "
            "con el día exacto; las muestras cercanas se etiquetan."
        )
    if used_ria:
        out.append(
            "Proxy RIA: ET0 y precipitación bruta de raw.raw_ria_clima_diario "
            "(RIA no publica PePMon; Pe ≈ precip bruta). Comparar con cautela frente a SiAR."
        )
    out.append(
        "SiAR es la fuente preferida; RIA solo rellena años sin cobertura SiAR suficiente."
    )
    return out


def _quantile(sorted_vals: list[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)


def empirical_percentiles(values: list[float]) -> dict[str, float | None]:
    s = sorted(float(v) for v in values)
    return {
        "p10": _f(_quantile(s, 0.10), 2),
        "p50": _f(_quantile(s, 0.50), 2),
        "p90": _f(_quantile(s, 0.90), 2),
    }


def percentile_rank(value: float, samples: list[float]) -> float | None:
    """Empirical percentile rank of `value` among `samples` (0–100).

    Samples should exclude the current year. Higher = more extreme for ET0/demand.
    """
    if not samples:
        return None
    n = len(samples)
    less = sum(1 for x in samples if x < value)
    equal = sum(1 for x in samples if abs(x - value) < 1e-12)
    return _f(100.0 * (less + 0.5 * equal) / n, 1)


def _confidence(n_years: int) -> str:
    if n_years >= MIN_YEARS_OK:
        return "ok"
    if n_years >= 2:
        return "low"
    if n_years == 1:
        return "very_low"
    return "none"


def _plain_es(
    *,
    metric_label: str,
    rank: float | None,
    current: float | None,
    mean_v: float | None,
    unit: str,
    n_years: int,
    context: str,
) -> str:
    if current is None:
        return f"Sin dato de {metric_label} para {context}."
    parts: list[str] = []
    if rank is not None and n_years >= 2:
        parts.append(
            f"Este año está en el percentil {rank:.0f} de {metric_label} ({context}): "
            f"más extremo que el {rank:.0f}% de los años disponibles."
        )
    if mean_v is not None and n_years >= 1:
        delta = current - mean_v
        sign = "+" if delta >= 0 else ""
        parts.append(
            f"Actual {current:.1f} {unit} frente a media de años disponibles "
            f"{mean_v:.1f} {unit} ({sign}{delta:.1f})."
        )
    if n_years < MIN_YEARS_OK:
        parts.append(
            f"Historial corto ({n_years} año{'s' if n_years != 1 else ''}): lectura orientativa."
        )
    return " ".join(parts) if parts else f"{metric_label}: sin comparación."


def _plain_en(
    *,
    metric_label: str,
    rank: float | None,
    current: float | None,
    mean_v: float | None,
    unit: str,
    n_years: int,
    context: str,
) -> str:
    if current is None:
        return f"No {metric_label} data for {context}."
    parts: list[str] = []
    if rank is not None and n_years >= 2:
        parts.append(
            f"This year is at percentile {rank:.0f} for {metric_label} ({context}): "
            f"more extreme than {rank:.0f}% of available years."
        )
    if mean_v is not None and n_years >= 1:
        delta = current - mean_v
        sign = "+" if delta >= 0 else ""
        parts.append(
            f"Current {current:.1f} {unit} vs mean of available years "
            f"{mean_v:.1f} {unit} ({sign}{delta:.1f})."
        )
    if n_years < MIN_YEARS_OK:
        parts.append(
            f"Short history ({n_years} year{'s' if n_years != 1 else ''}): indicative only."
        )
    return " ".join(parts) if parts else f"{metric_label}: no comparison."


def _metric_block(
    *,
    current: float | None,
    samples: list[dict[str, Any]],
    unit: str,
    metric_label_es: str,
    metric_label_en: str,
    context_es: str,
    context_en: str,
) -> dict[str, Any]:
    vals = [float(s["value"]) for s in samples if s.get("value") is not None]
    n_years = len({int(s["year"]) for s in samples})
    mean_v = (sum(vals) / len(vals)) if vals else None
    pcts = empirical_percentiles(vals)
    rank = percentile_rank(float(current), vals) if current is not None and vals else None
    # Rank among prior years only (exclude current from samples for rank)
    prior_vals = [
        float(s["value"])
        for s in samples
        if s.get("value") is not None and not s.get("is_current")
    ]
    if prior_vals and current is not None:
        rank = percentile_rank(float(current), prior_vals)
        mean_prior = sum(prior_vals) / len(prior_vals)
        # Prefer prior-year mean for "vs mean" when we have priors
        mean_v = mean_prior
        pcts = empirical_percentiles(prior_vals)
        n_compare = len({int(s["year"]) for s in samples if not s.get("is_current")})
    else:
        n_compare = n_years

    conf = _confidence(max(n_compare, 1 if current is not None else 0))
    return {
        "current": _f(current, 2) if current is not None else None,
        "mean_available": _f(mean_v, 2) if mean_v is not None else None,
        "p10": pcts["p10"],
        "p50": pcts["p50"],
        "p90": pcts["p90"],
        "percentile_rank": rank,
        "n_years": n_compare,
        "n_samples": len(prior_vals) if prior_vals else len(vals),
        "confidence": conf,
        "unit": unit,
        "samples": samples,
        "plain_es": _plain_es(
            metric_label=metric_label_es,
            rank=rank,
            current=current,
            mean_v=mean_v,
            unit=unit,
            n_years=max(n_compare, 1 if current is not None else 0),
            context=context_es,
        ),
        "plain_en": _plain_en(
            metric_label=metric_label_en,
            rank=rank,
            current=current,
            mean_v=mean_v,
            unit=unit,
            n_years=max(n_compare, 1 if current is not None else 0),
            context=context_en,
        ),
    }


def _coverage_meta(conn: Connection) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "siar_years": [],
        "ria_proxy_years": [],
        "siar_min_fecha": None,
        "siar_max_fecha": None,
        "ria_min_fecha": None,
        "ria_max_fecha": None,
        "n_years_total": 0,
        "confidence": "none",
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


def _years_with_data(conn: Connection) -> tuple[list[int], list[int]]:
    """Return (siar_years, ria_years) that have any ET0 rows."""
    siar_y: list[int] = []
    ria_y: list[int] = []
    try:
        rows = _rows(
            conn,
            """
            SELECT DISTINCT EXTRACT(YEAR FROM fecha)::int AS y
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND' AND et0 IS NOT NULL
            ORDER BY 1
            """,
        )
        siar_y = [int(r["y"]) for r in rows if r.get("y") is not None]
    except Exception:  # noqa: BLE001
        pass
    try:
        rows = _rows(
            conn,
            """
            SELECT DISTINCT EXTRACT(YEAR FROM fecha)::int AS y
            FROM raw.raw_ria_clima_diario
            WHERE et0 IS NOT NULL
            ORDER BY 1
            """,
        )
        ria_y = [int(r["y"]) for r in rows if r.get("y") is not None]
    except Exception:  # noqa: BLE001
        pass
    return siar_y, ria_y


def _load_daily_means(
    conn: Connection,
    *,
    source: str,
    start: date,
    end: date,
) -> dict[str, list[dict[str, Any]]]:
    if end < start:
        return {}
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


def _safe_md(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        try:
            return date(year, month, 28)
        except ValueError:
            return None


def _pick_doy_day(
    days: list[dict[str, Any]],
    *,
    month: int,
    day: int,
    half_window: int,
) -> tuple[dict[str, Any] | None, int]:
    """Pick the day closest to month/day within ±half_window. Returns (row, offset_days)."""
    if not days:
        return None, 0
    by_date: dict[str, dict[str, Any]] = {d["date"]: d for d in days}
    # infer year from first day
    y = int(days[0]["date"][:4])
    target = _safe_md(y, month, day)
    if not target:
        return None, 0
    best: dict[str, Any] | None = None
    best_off = 999
    for off in range(0, half_window + 1):
        for sign in (0, -1, 1) if off == 0 else (-1, 1):
            if off == 0 and sign != 0:
                continue
            cand = target + timedelta(days=sign * off)
            row = by_date.get(cand.isoformat())
            if row is not None and abs(sign * off) < best_off:
                best = row
                best_off = abs(sign * off)
                if best_off == 0:
                    return best, 0
    return best, best_off if best is not None else 0


def _accumulate_window(
    daily_by_prov: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], int]:
    by_province: dict[str, dict[str, Any]] = {}
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
        by_province[province] = {
            "province_name": province,
            "irrigated_ha": ha,
            "kc": _f(kc, 2),
            "days_with_data": len(days),
            "cum_et0_mm": et0_sum,
            "cum_pe_mm": pe_sum,
            "cum_net_demand_mm": net_mm_sum,
            "cum_demand_hm3": demand_hm3,
        }
        total_hm3 += demand_hm3
        total_ha += ha

    weighted_net = 0.0
    weighted_et0 = 0.0
    weighted_pe = 0.0
    w = 0
    for p in by_province.values():
        ha = int(p["irrigated_ha"] or 0)
        weighted_net += float(p["cum_net_demand_mm"] or 0) * ha
        weighted_et0 += float(p["cum_et0_mm"] or 0) * ha
        weighted_pe += float(p["cum_pe_mm"] or 0) * ha
        w += ha

    regional = {
        "province_name": "Andalucía",
        "irrigated_ha": total_ha,
        "days_with_data": len(all_dates),
        "cum_et0_mm": (weighted_et0 / w) if w else None,
        "cum_pe_mm": (weighted_pe / w) if w else None,
        "cum_net_demand_mm": (weighted_net / w) if w else None,
        "cum_demand_hm3": total_hm3 if by_province else None,
    }
    return regional, by_province, len(all_dates)


def _spot_from_day(
    day: dict[str, Any] | None, kc: float
) -> tuple[float | None, float | None, float | None]:
    if not day:
        return None, None, None
    et0 = float(day["et0_mm"])
    pe = float(day["pe_mm"])
    net = kc * max(0.0, et0 - pe)
    return et0, pe, net


def _regional_spot(
    by_prov_spots: dict[str, tuple[float | None, float | None, float | None, float, int]],
) -> tuple[float | None, float | None, float | None]:
    """Ha-weighted regional ET0 / Pe / net mm from province spots."""
    w = 0
    et0_w = 0.0
    pe_w = 0.0
    net_w = 0.0
    for et0, pe, net, _kc, ha in by_prov_spots.values():
        if et0 is None:
            continue
        et0_w += et0 * ha
        pe_w += (pe or 0) * ha
        net_w += (net or 0) * ha
        w += ha
    if not w:
        return None, None, None
    return et0_w / w, pe_w / w, net_w / w


def build_climate_percentiles(
    conn: Connection,
    *,
    as_of: str | date | None = None,
) -> dict[str, Any]:
    """Build same-DOY and campaign-to-date ET0/demand percentiles."""
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
                out["note_es"] = "Sin fechas SiAR/RIA para anclar los percentiles."
                out["caveats_es"] = _caveats(used_ria=False, thin=True, doy_window=0)
                return out
            as_of_d = _parse_date(as_of_s)
        else:
            as_of_d = _parse_date(as_of) if not isinstance(as_of, date) else as_of
        if not as_of_d:
            out["note_es"] = "Fecha de referencia no válida."
            return out

        current_year = as_of_d.year
        ref_month, ref_day = as_of_d.month, as_of_d.day
        # Cap campaign end for through_doy display
        camp_end = date(current_year, CAMPAIGN_END_MONTH, CAMPAIGN_END_DAY)
        ref_for_campaign = as_of_d if as_of_d <= camp_end else camp_end
        campaign_started = (as_of_d.month, as_of_d.day) >= (
            CAMPAIGN_START_MONTH,
            CAMPAIGN_START_DAY,
        )

        coverage = _coverage_meta(conn)
        siar_years_all, ria_years_all = _years_with_data(conn)
        year_lo = current_year - LOOKBACK_YEARS
        candidate_years = sorted(
            {
                y
                for y in set(siar_years_all) | set(ria_years_all)
                if year_lo <= y <= current_year
            }
        )

        out["as_of"] = as_of_d.isoformat()
        out["current_year"] = current_year
        out["through_doy"] = {
            "month": ref_month,
            "day": ref_day,
            "label": f"{ref_day:02d}/{ref_month:02d}",
        }

        # ---- Load per-year daily series (prefer SiAR) ----
        year_payloads: list[dict[str, Any]] = []
        used_ria = False
        siar_used: list[int] = []
        ria_used: list[int] = []

        for y in candidate_years:
            # Full calendar year slice for DOY; campaign window separately
            y_start = date(y, 1, 1)
            y_end = date(y, 12, 31) if y < current_year else as_of_d
            # Prefer SiAR if any days that year
            use_siar = y in siar_years_all
            source = "siar" if use_siar else "ria"
            source_key = "siar" if use_siar else "ria_proxy"
            source_label = "SiAR (MAPA)" if use_siar else "RIA (proxy ET0; Pe≈precip)"
            if not use_siar:
                used_ria = True
                if y not in ria_years_all:
                    continue

            daily = _load_daily_means(conn, source=source, start=y_start, end=y_end)
            if not daily:
                # try other source
                alt = "ria" if source == "siar" else "siar"
                if alt == "ria" and y in ria_years_all:
                    daily = _load_daily_means(conn, source="ria", start=y_start, end=y_end)
                    source = "ria"
                    source_key = "ria_proxy"
                    source_label = "RIA (proxy ET0; Pe≈precip)"
                    used_ria = True
                elif alt == "siar" and y in siar_years_all:
                    daily = _load_daily_means(conn, source="siar", start=y_start, end=y_end)
                    source = "siar"
                    source_key = "siar"
                    source_label = "SiAR (MAPA)"
            if not daily:
                continue

            if source_key == "siar":
                siar_used.append(y)
            else:
                ria_used.append(y)

            # Campaign window
            c_start = date(y, CAMPAIGN_START_MONTH, CAMPAIGN_START_DAY)
            try:
                c_through = date(y, ref_for_campaign.month, ref_for_campaign.day)
            except ValueError:
                c_through = date(y, ref_for_campaign.month, 28)
            c_end_cap = date(y, CAMPAIGN_END_MONTH, CAMPAIGN_END_DAY)
            if c_through > c_end_cap:
                c_through = c_end_cap
            campaign_daily: dict[str, list[dict[str, Any]]] = {}
            if campaign_started or y < current_year:
                if c_through >= c_start:
                    for prov, days in daily.items():
                        campaign_daily[prov] = [
                            d
                            for d in days
                            if c_start.isoformat() <= d["date"] <= c_through.isoformat()
                        ]

            year_payloads.append(
                {
                    "year": y,
                    "source": source_key,
                    "source_label_es": source_label,
                    "is_current": y == current_year,
                    "daily": daily,
                    "campaign_daily": campaign_daily,
                    "campaign_start": c_start.isoformat() if campaign_daily else None,
                    "campaign_end": c_through.isoformat() if campaign_daily else None,
                }
            )

        coverage["siar_years"] = siar_used
        coverage["ria_proxy_years"] = ria_used
        coverage["n_years_total"] = len(year_payloads)
        coverage["confidence"] = _confidence(len(year_payloads))
        out["coverage"] = coverage

        thin = len(year_payloads) < MIN_YEARS_OK

        # Decide DOY window expansion
        # Count exact-DOY provincial hits for regional presence
        exact_hits = 0
        for yp in year_payloads:
            if yp["year"] == current_year:
                continue
            for days in yp["daily"].values():
                row, off = _pick_doy_day(days, month=ref_month, day=ref_day, half_window=0)
                if row is not None:
                    exact_hits += 1
                    break
        doy_half = (
            DOY_WINDOW_HALF_EXPANDED
            if exact_hits < DOY_WINDOW_EXPAND_IF_BELOW
            else 0
        )

        out["caveats_es"] = _caveats(used_ria=used_ria, thin=thin, doy_window=doy_half)
        out["method_es"] = (
            "Para cada año con dato se toma el ET0 medio provincial (SiAR preferido; "
            "RIA proxy si falta) el mismo día del calendario"
            + (f" (±{doy_half} d)" if doy_half else "")
            + " y la demanda neta Kc×max(0,ET0−Pe). "
            "La campaña acumula desde el 1 de abril hasta el mismo DOY. "
            "Percentil empírico = rango del valor actual entre años previos "
            "(P10/P50/P90 de la muestra previa). No se inventan huecos."
        )

        if not year_payloads:
            out["note_es"] = (
                "No hay años con ET0 en SiAR/RIA dentro de la ventana de lookback."
            )
            return out

        # ---- Build same_doy + campaign samples per province ----
        provinces = sorted(IRRIGATED_HA_2023.keys())

        def build_scope(province: str | None) -> dict[str, Any]:
            """province=None → regional Andalucía."""
            name = province or "Andalucía"
            kc = (
                float(KC_BY_PROVINCE.get(province, DEFAULT_KC))
                if province
                else DEFAULT_KC
            )
            ha = int(IRRIGATED_HA_2023[province]) if province else sum(
                IRRIGATED_HA_2023.values()
            )

            et0_samples: list[dict[str, Any]] = []
            net_samples: list[dict[str, Any]] = []
            cum_et0_samples: list[dict[str, Any]] = []
            cum_net_samples: list[dict[str, Any]] = []
            cum_hm3_samples: list[dict[str, Any]] = []

            current_et0 = current_net = None
            current_cum_et0 = current_cum_net = current_cum_hm3 = None
            current_source = None
            doy_date_used = None

            for yp in year_payloads:
                y = yp["year"]
                src = yp["source"]
                if province:
                    days = yp["daily"].get(province) or []
                    row, off = _pick_doy_day(
                        days, month=ref_month, day=ref_day, half_window=doy_half
                    )
                    et0, _pe, net = _spot_from_day(row, kc)
                    sample_date = row["date"] if row else None
                else:
                    # regional: ha-weighted from each province that day
                    spots: dict[
                        str, tuple[float | None, float | None, float | None, float, int]
                    ] = {}
                    sample_date = None
                    off = 0
                    for p_name in provinces:
                        p_kc = float(KC_BY_PROVINCE.get(p_name, DEFAULT_KC))
                        p_ha = int(IRRIGATED_HA_2023[p_name])
                        days = yp["daily"].get(p_name) or []
                        row, off_p = _pick_doy_day(
                            days, month=ref_month, day=ref_day, half_window=doy_half
                        )
                        et0_p, pe_p, net_p = _spot_from_day(row, p_kc)
                        if et0_p is not None:
                            spots[p_name] = (et0_p, pe_p, net_p, p_kc, p_ha)
                            if sample_date is None and row:
                                sample_date = row["date"]
                                off = off_p
                    et0, _pe, net = _regional_spot(spots)

                if et0 is not None:
                    base = {
                        "year": y,
                        "source": src,
                        "date": sample_date,
                        "doy_offset_days": off,
                        "is_current": yp["is_current"],
                    }
                    et0_samples.append({**base, "value": _f(et0, 2)})
                    if net is not None:
                        net_samples.append({**base, "value": _f(net, 2)})
                    if yp["is_current"]:
                        current_et0 = et0
                        current_net = net
                        current_source = src
                        doy_date_used = sample_date

                # Campaign cumulative
                if not yp["campaign_daily"]:
                    continue
                if province:
                    c_days = yp["campaign_daily"].get(province) or []
                    if len(c_days) < 1:
                        continue
                    reg, byp, n_days = _accumulate_window({province: c_days})
                    prov_row = byp.get(province)
                    if not prov_row or n_days < 1:
                        continue
                    # For partial campaign in current year allow short; for priors require MIN
                    if not yp["is_current"] and n_days < MIN_CAMPAIGN_DAYS:
                        continue
                    c_et0 = float(prov_row["cum_et0_mm"])
                    c_net = float(prov_row["cum_net_demand_mm"])
                    c_hm3 = float(prov_row["cum_demand_hm3"])
                else:
                    reg, _byp, n_days = _accumulate_window(yp["campaign_daily"])
                    if reg.get("cum_et0_mm") is None or n_days < 1:
                        continue
                    if not yp["is_current"] and n_days < MIN_CAMPAIGN_DAYS:
                        continue
                    c_et0 = float(reg["cum_et0_mm"])
                    c_net = float(reg["cum_net_demand_mm"] or 0)
                    c_hm3 = float(reg["cum_demand_hm3"] or 0)

                s_c = {
                    "year": y,
                    "source": src,
                    "window_start": yp["campaign_start"],
                    "window_end": yp["campaign_end"],
                    "days_with_data": n_days,
                    "is_current": yp["is_current"],
                }
                cum_et0_samples.append({**s_c, "value": _f(c_et0, 1)})
                cum_net_samples.append({**s_c, "value": _f(c_net, 1)})
                cum_hm3_samples.append({**s_c, "value": _f(c_hm3, 2)})
                if yp["is_current"]:
                    current_cum_et0 = c_et0
                    current_cum_net = c_net
                    current_cum_hm3 = c_hm3

            doy_label = f"{ref_day:02d}/{ref_month:02d}"
            et0_block = _metric_block(
                current=current_et0,
                samples=et0_samples,
                unit="mm",
                metric_label_es="ET0",
                metric_label_en="ET0",
                context_es=f"mismo DOY {doy_label}",
                context_en=f"same DOY {doy_label}",
            )
            net_block = _metric_block(
                current=current_net,
                samples=net_samples,
                unit="mm",
                metric_label_es="demanda neta",
                metric_label_en="net demand",
                context_es=f"mismo DOY {doy_label}",
                context_en=f"same DOY {doy_label}",
            )
            cum_et0_block = _metric_block(
                current=current_cum_et0,
                samples=cum_et0_samples,
                unit="mm",
                metric_label_es="ET0 acumulado",
                metric_label_en="cumulative ET0",
                context_es="campaña abr→hoy",
                context_en="campaign Apr→today",
            )
            cum_net_block = _metric_block(
                current=current_cum_net,
                samples=cum_net_samples,
                unit="mm",
                metric_label_es="demanda neta acumulada",
                metric_label_en="cumulative net demand",
                context_es="campaña abr→hoy",
                context_en="campaign Apr→today",
            )
            cum_hm3_block = _metric_block(
                current=current_cum_hm3,
                samples=cum_hm3_samples,
                unit="hm³",
                metric_label_es="demanda acumulada",
                metric_label_en="cumulative demand",
                context_es="campaña abr→hoy",
                context_en="campaign Apr→today",
            )

            # Headline: prefer campaign net demand rank, else same-DOY ET0
            focus = cum_net_block if cum_net_block.get("current") is not None else et0_block
            headline_es = focus.get("plain_es") or ""
            headline_en = focus.get("plain_en") or ""

            return {
                "province_name": name,
                "irrigated_ha": ha,
                "kc": _f(kc, 2) if province else None,
                "source_current": current_source,
                "same_doy": {
                    "date_label": doy_label,
                    "date_used": doy_date_used,
                    "doy_window_half_days": doy_half,
                    "et0": et0_block,
                    "net_demand_mm": net_block,
                },
                "campaign_to_date": {
                    "window_label_es": "Campaña agrícola abr–sep (hasta hoy)",
                    "et0_cum": cum_et0_block,
                    "net_demand_mm_cum": cum_net_block,
                    "demand_hm3_cum": cum_hm3_block,
                },
                "headline_es": headline_es,
                "headline_en": headline_en,
            }

        regional = build_scope(None)
        by_province = [build_scope(p) for p in provinces]
        # Drop provinces with no current and no samples
        by_province = [
            p
            for p in by_province
            if (p["same_doy"]["et0"].get("current") is not None)
            or (p["same_doy"]["et0"].get("n_samples") or 0) > 0
            or (p["campaign_to_date"]["net_demand_mm_cum"].get("current") is not None)
        ]
        def _rank_key(r: dict[str, Any]) -> float:
            for path in (
                ("campaign_to_date", "demand_hm3_cum"),
                ("campaign_to_date", "net_demand_mm_cum"),
                ("same_doy", "et0"),
            ):
                block = r
                for k in path:
                    block = (block or {}).get(k)  # type: ignore[assignment]
                if isinstance(block, dict) and block.get("percentile_rank") is not None:
                    return float(block["percentile_rank"])
            return 0.0

        by_province.sort(key=_rank_key, reverse=True)

        out["regional"] = regional
        out["by_province"] = by_province
        out["headline_es"] = regional.get("headline_es") or ""
        out["headline_en"] = regional.get("headline_en") or ""

        sources_note = []
        if siar_used:
            sources_note.append("SiAR años: " + ", ".join(str(y) for y in siar_used))
        if ria_used:
            sources_note.append(
                "RIA proxy años: " + ", ".join(str(y) for y in ria_used)
            )
        out["note_es"] = (
            f"Normales / percentiles ET0 y demanda neta a {ref_day:02d}/{ref_month:02d}. "
            + (" · ".join(sources_note) if sources_note else "")
        )
        # Available if we have at least current OR any comparison samples
        has_any = bool(
            regional["same_doy"]["et0"].get("current") is not None
            or (regional["same_doy"]["et0"].get("n_samples") or 0) > 0
            or regional["campaign_to_date"]["net_demand_mm_cum"].get("current") is not None
        )
        out["available"] = has_any
        if not has_any:
            out["note_es"] = (
                "Hay cobertura SiAR/RIA pero no se pudo formar la muestra de DOY/campaña."
            )
        return out
    except Exception as exc:  # noqa: BLE001
        out["note_es"] = f"Error calculando percentiles climáticos: {exc}"
        out["caveats_es"] = _caveats(used_ria=False, thin=True, doy_window=0)
        return out
