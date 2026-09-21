"""Precipitación efectiva (Pe / PePMon) vs precipitación bruta SiAR.

Prioridad:
1) Campo oficial SiAR PePMon → columna raw.precip_efectiva (Penman-Monteith / datos
   calculados del MAPA cuando DatosCalculados=true en la ingesta).
2) Si no hay PePMon en el día (ninguna estación con precip_efectiva), estimación
   transparente USDA-SCS (curva clásica mensual aplicada al mm diario) — siempre
   etiquetada como estimación, nunca como PePMon oficial.

La autonomía / crop_etc siguen usando pe_mm coalescido a 0 (conservador).
Este bloque es solo de lectura explicativa para el panel de Riego.
"""

from __future__ import annotations

from typing import Any


def _f(v: Any, nd: int = 2) -> float | None:
    if v is None:
        return None
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


def usda_scs_pe_mm(precip_mm: float) -> float:
    """USDA-SCS effective precipitation (mm).

    Classic monthly curve (SCS / USDA):
      Pe = P·(125 − 0.2·P)/125   if P < 250 mm
      Pe = 125 + 0.1·P           if P ≥ 250 mm

    Applied here per day as a documented fallback when SiAR PePMon is absent.
    Not an official MAPA/SiAR value.
    """
    p = max(0.0, float(precip_mm or 0))
    if p <= 0:
        return 0.0
    if p < 250.0:
        return p * (125.0 - 0.2 * p) / 125.0
    return 125.0 + 0.1 * p


def _ratio(pe: float, precip: float) -> float | None:
    if precip <= 1e-9:
        return None
    return max(0.0, min(1.0, pe / precip))


def _empty(as_of: str | None = None) -> dict[str, Any]:
    return {
        "available": False,
        "as_of": as_of,
        "unit": "mm",
        "source_preferred": "siar_pepmon",
        "formula_es": (
            "Preferencia: Pe = PePMon SiAR (raw.precip_efectiva). "
            "Reserva: Pe_est USDA-SCS = P·(125−0,2·P)/125 (P<250) o 125+0,1·P."
        ),
        "note_es": "Sin historial SiAR para precipitación efectiva.",
        "caveats_es": [
            "PePMon SiAR es el valor calculado por el MAPA (API DatosCalculados); "
            "no lo inventamos nosotros cuando está presente.",
            "Si falta PePMon en un día, la estimación USDA-SCS es orientativa "
            "(curva pensada para totales mensuales; aquí se aplica al mm diario).",
            "Ratio Pe/P < 1 no implica error: escorrentía, intercepción y "
            "humedad previa hacen que no toda la lluvia bruta entre al suelo/regadío.",
            "Media provincial de estaciones SiAR; no es un balance de parcela.",
        ],
        "definition_es": (
            "Precipitación bruta = lluvia medida. Precipitación efectiva (Pe) = "
            "cuánto de esa lluvia suele quedar disponible para el suelo/cultivo. "
            "Cuando hay PePMon SiAR lo usamos; si no, estimamos y lo etiquetamos."
        ),
        "regional": None,
        "by_province": [],
    }


def _pack_scope(
    *,
    province_name: str,
    series: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not series:
        return None
    last = series[-1]
    tail7 = series[-7:]
    tail30 = series[-30:]
    precip_7 = sum(float(x["precip_mm"] or 0) for x in tail7)
    pe_7 = sum(float(x["pe_mm"] or 0) for x in tail7)
    precip_30 = sum(float(x["precip_mm"] or 0) for x in tail30)
    pe_30 = sum(float(x["pe_mm"] or 0) for x in tail30)
    sources_7 = {str(x.get("source") or "") for x in tail7}
    if sources_7 == {"siar_pepmon"}:
        source_window = "siar_pepmon"
    elif "siar_pepmon" in sources_7 and "estimacion_usda_scs" in sources_7:
        source_window = "mixed"
    elif "estimacion_usda_scs" in sources_7:
        source_window = "estimacion_usda_scs"
    else:
        source_window = last.get("source") or "unknown"

    return {
        "province_name": province_name,
        "as_of": last["date"],
        "precip_mm": last["precip_mm"],
        "pe_mm": last["pe_mm"],
        "pe_pmon_mm": last.get("pe_pmon_mm"),
        "pe_est_mm": last.get("pe_est_mm"),
        "effective_precip_mm": last["pe_mm"],
        "lost_mm": last["lost_mm"],
        "ratio_pe_over_p": last["ratio_pe_over_p"],
        "source": last.get("source"),
        "source_window_7d": source_window,
        "precip_7d_mm": _f(precip_7, 1),
        "pe_7d_mm": _f(pe_7, 1),
        "ratio_7d": _f(_ratio(pe_7, precip_7), 3),
        "precip_30d_mm": _f(precip_30, 1),
        "pe_30d_mm": _f(pe_30, 1),
        "ratio_30d": _f(_ratio(pe_30, precip_30), 3),
        "days_in_7d": len(tail7),
        "days_in_30d": len(tail30),
        "pe_station_count": last.get("pe_station_count"),
        "station_count": last.get("station_count"),
        "series": series,
    }


def build_effective_precip(
    siar_hist: dict[str, list[dict[str, Any]]],
    *,
    as_of: str | None,
) -> dict[str, Any]:
    """Compare gross precip vs effective Pe (PePMon or USDA estimate)."""
    empty = _empty(as_of)
    if not siar_hist:
        return empty

    by_province: list[dict[str, Any]] = []
    for name, hist in sorted(siar_hist.items()):
        if not hist:
            continue
        series: list[dict[str, Any]] = []
        for d in hist:
            precip = float(d.get("precip_mm") or 0)
            pe_n = int(d.get("pe_n") or 0)
            pe_raw = d.get("pe_raw_mm")
            pe_coalesced = float(d.get("pe_mm") or 0)
            pe_est = usda_scs_pe_mm(precip)

            if pe_n > 0 and pe_raw is not None:
                pe = float(pe_raw)
                pe_pmon = pe
                source = "siar_pepmon"
            elif pe_n > 0:
                # History without pe_raw but pe_n present — trust coalesced pe_mm.
                pe = pe_coalesced
                pe_pmon = pe
                source = "siar_pepmon"
            else:
                pe = pe_est
                pe_pmon = None
                source = "estimacion_usda_scs"

            ratio = _ratio(pe, precip)
            series.append(
                {
                    "date": d["date"],
                    "precip_mm": _f(precip, 2),
                    "pe_mm": _f(pe, 2),
                    "pe_pmon_mm": _f(pe_pmon, 2) if pe_pmon is not None else None,
                    "pe_est_mm": _f(pe_est, 2),
                    "lost_mm": _f(max(0.0, precip - pe), 2),
                    "ratio_pe_over_p": _f(ratio, 3) if ratio is not None else None,
                    "source": source,
                    "pe_station_count": pe_n,
                    "station_count": int(d.get("station_count") or 0),
                }
            )
        packed = _pack_scope(province_name=name, series=series)
        if packed:
            by_province.append(packed)

    if not by_province:
        return empty

    # Regional: mean of provincial daily series aligned by date.
    dates = sorted({d["date"] for p in by_province for d in p["series"]})
    series_r: list[dict[str, Any]] = []
    for dt in dates:
        rows = []
        for p in by_province:
            hit = next((x for x in p["series"] if x["date"] == dt), None)
            if hit:
                rows.append(hit)
        if not rows:
            continue
        n = len(rows)
        precip = sum(float(x["precip_mm"] or 0) for x in rows) / n
        pe = sum(float(x["pe_mm"] or 0) for x in rows) / n
        pe_pmon_vals = [float(x["pe_pmon_mm"]) for x in rows if x.get("pe_pmon_mm") is not None]
        pe_est = sum(float(x["pe_est_mm"] or 0) for x in rows) / n
        sources = {str(x.get("source") or "") for x in rows}
        if sources == {"siar_pepmon"}:
            source = "siar_pepmon"
        elif "estimacion_usda_scs" in sources and "siar_pepmon" in sources:
            source = "mixed"
        elif sources == {"estimacion_usda_scs"}:
            source = "estimacion_usda_scs"
        else:
            source = "mixed"
        ratio = _ratio(pe, precip)
        series_r.append(
            {
                "date": dt,
                "precip_mm": _f(precip, 2),
                "pe_mm": _f(pe, 2),
                "pe_pmon_mm": _f(sum(pe_pmon_vals) / len(pe_pmon_vals), 2)
                if pe_pmon_vals
                else None,
                "pe_est_mm": _f(pe_est, 2),
                "lost_mm": _f(max(0.0, precip - pe), 2),
                "ratio_pe_over_p": _f(ratio, 3) if ratio is not None else None,
                "source": source,
                "pe_station_count": sum(int(x.get("pe_station_count") or 0) for x in rows),
                "station_count": sum(int(x.get("station_count") or 0) for x in rows),
            }
        )

    regional = _pack_scope(province_name="Andalucía", series=series_r)
    used_siar = any(
        (p.get("source") == "siar_pepmon") or (p.get("source_window_7d") in ("siar_pepmon", "mixed"))
        for p in by_province
    )
    note = (
        "Pe desde PePMon SiAR (precip_efectiva) cuando hay dato de estación; "
        "si falta, estimación USDA-SCS etiquetada."
        if used_siar
        else "Sin PePMon en la ventana: se muestra estimación USDA-SCS (no oficial)."
    )

    return {
        "available": True,
        "as_of": as_of,
        "unit": "mm",
        "source_preferred": "siar_pepmon",
        "formula_es": empty["formula_es"],
        "note_es": note,
        "caveats_es": empty["caveats_es"],
        "definition_es": empty["definition_es"],
        "regional": regional,
        "by_province": by_province,
    }
