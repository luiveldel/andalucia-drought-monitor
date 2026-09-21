"""Necesidades por cultivo (ETc = Kc × ET0 SiAR).

Extiende el Kc provincial ya usado en autonomía: aquí se calcula ETc para un
conjunto pequeño de cultivos representativos andaluces y se compara con
señales de agua disponibles (stock embalsado / ha, demanda base, burn).

No hay tablas oficiales de dotación/restricción en este piloto: los ratios
se etiquetan explícitamente como estimación / proxy.
"""

from __future__ import annotations

from typing import Any

# Keep this module free of SQLAlchemy / heavy irrigation imports.
DEFAULT_KC = 0.75
MM_HA_TO_HM3 = 1e-5


def _f(v, nd: int = 2):
    if v is None:
        return None
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None

# Kc de media estación (aprox.) — fuentes en plain Spanish en source_es.
# FAO-56: Allen et al. (1998) Crop evapotranspiration. MAPA/SiAR App y
# tablas regionales andaluzas usan valores similares para riego de referencia.
CROPS: list[dict[str, Any]] = [
    {
        "id": "olivar",
        "name_es": "Olivar",
        "name_en": "Olive grove",
        "kc": 0.70,
        "source_es": (
            "Kc ~0,70 en plena actividad (FAO-56 olivo; práctica andaluza de riego). "
            "En invierno o con estrés el cultivo pide menos."
        ),
    },
    {
        "id": "citricos",
        "name_es": "Cítricos",
        "name_en": "Citrus",
        "kc": 0.70,
        "source_es": (
            "Kc ~0,70 en media estación (FAO-56 cítricos adultos). "
            "Varía con el marco y si hay cubierta vegetal."
        ),
    },
    {
        "id": "horticolas",
        "name_es": "Hortícolas (aire libre / invernadero)",
        "name_en": "Vegetables (open field / greenhouse)",
        "kc": 1.05,
        "source_es": (
            "Kc ~1,05 como media de hortícolas en pleno desarrollo (FAO-56 / SiAR App). "
            "Invernadero intensivo puede pedir aún más en picos."
        ),
    },
    {
        "id": "algodon",
        "name_es": "Algodón",
        "name_en": "Cotton",
        "kc": 1.15,
        "source_es": (
            "Kc ~1,15 en media estación (FAO-56 algodón). "
            "Típico del Valle del Guadalquivir en verano."
        ),
    },
    {
        "id": "maiz",
        "name_es": "Maíz",
        "name_en": "Maize",
        "kc": 1.20,
        "source_es": (
            "Kc ~1,20 en media estación (FAO-56 maíz). "
            "Cultivo muy exigente en los meses de máximo calor."
        ),
    },
    {
        "id": "fresa",
        "name_es": "Fresa / berries",
        "name_en": "Strawberry / berries",
        "kc": 0.85,
        "source_es": (
            "Kc ~0,85 orientativo para fresa/berries en producción (tablas SiAR / práctica onubense). "
            "El invernadero y el tipo de sustrato cambian mucho la cifra."
        ),
    },
]


def _empty() -> dict[str, Any]:
    return {
        "available": False,
        "as_of_siar": None,
        "formula_es": "ETc (mm) = Kc × ET0_SiAR",
        "note_es": "",
        "caveats_es": [],
        "kc_table": [],
        "crops_meta": [],
        "regional": None,
        "by_province": [],
    }


def _stock_mm(stored_hm3: float | None, irrigated_ha: int | None) -> float | None:
    """Proxy: mm si se repartiera el volumen usable sobre las ha de regadío."""
    if stored_hm3 is None or irrigated_ha is None or irrigated_ha <= 0:
        return None
    return float(stored_hm3) / (float(irrigated_ha) * MM_HA_TO_HM3)


def _crop_row(
    *,
    crop: dict[str, Any],
    et0_mm: float,
    pe_mm: float,
    irrigated_ha: int,
    stored_hm3: float | None,
    baseline_kc: float,
    baseline_demand_hm3: float | None,
    days_autonomy: float | None,
    burn_hm3_per_day: float | None,
) -> dict[str, Any]:
    kc = float(crop["kc"])
    etc_mm = kc * et0_mm
    etc_net_mm = max(0.0, etc_mm - pe_mm)
    demand_hm3 = etc_net_mm * irrigated_ha * MM_HA_TO_HM3
    stock = _stock_mm(stored_hm3, irrigated_ha)
    cover_days = None
    if stock is not None and etc_net_mm > 1e-9:
        cover_days = stock / etc_net_mm

    baseline_etc_mm = baseline_kc * et0_mm
    vs_baseline = (etc_mm / baseline_etc_mm) if baseline_etc_mm > 1e-9 else None
    vs_demand = None
    if baseline_demand_hm3 is not None and baseline_demand_hm3 > 1e-9:
        vs_demand = demand_hm3 / float(baseline_demand_hm3)

    burn_vs_crop = None
    if burn_hm3_per_day is not None and demand_hm3 > 1e-9:
        burn_vs_crop = float(burn_hm3_per_day) / demand_hm3

    pressure = "unknown"
    if cover_days is not None:
        if cover_days < 21:
            pressure = "high"
        elif cover_days < 60:
            pressure = "medium"
        elif cover_days < 90:
            pressure = "watch"
        else:
            pressure = "low"

    return {
        "crop_id": crop["id"],
        "name_es": crop["name_es"],
        "name_en": crop["name_en"],
        "kc": _f(kc, 2),
        "etc_mm": _f(etc_mm, 2),
        "etc_net_mm": _f(etc_net_mm, 2),
        "etc_7d_est_mm": _f(etc_mm * 7.0, 1),
        "demand_hm3_if_all_ha": _f(demand_hm3, 3),
        "stock_proxy_mm": _f(stock, 1),
        "cover_days_proxy": _f(cover_days, 1),
        "vs_baseline_kc_ratio": _f(vs_baseline, 2),
        "vs_baseline_demand_ratio": _f(vs_demand, 2),
        "burn_vs_crop_demand_ratio": _f(burn_vs_crop, 2),
        "baseline_days_autonomy": _f(days_autonomy, 1),
        "pressure": pressure,
    }


def _pack_scope(
    *,
    province_name: str,
    et0_mm: float,
    pe_mm: float,
    irrigated_ha: int,
    stored_hm3: float | None,
    baseline_kc: float,
    baseline_demand_hm3: float | None,
    days_autonomy: float | None,
    burn_hm3_per_day: float | None,
) -> dict[str, Any]:
    crops = [
        _crop_row(
            crop=c,
            et0_mm=et0_mm,
            pe_mm=pe_mm,
            irrigated_ha=irrigated_ha,
            stored_hm3=stored_hm3,
            baseline_kc=baseline_kc,
            baseline_demand_hm3=baseline_demand_hm3,
            days_autonomy=days_autonomy,
            burn_hm3_per_day=burn_hm3_per_day,
        )
        for c in CROPS
    ]
    # Sort by ETc descending so thirsty crops surface first
    crops.sort(key=lambda r: -(r.get("etc_mm") or 0))
    return {
        "province_name": province_name,
        "et0_mm": _f(et0_mm, 2),
        "pe_mm": _f(pe_mm, 2),
        "irrigated_ha": irrigated_ha,
        "stored_hm3": _f(stored_hm3, 2) if stored_hm3 is not None else None,
        "baseline_kc": _f(baseline_kc, 2),
        "stock_proxy_mm": _f(_stock_mm(stored_hm3, irrigated_ha), 1),
        "crops": crops,
    }


def build_crop_etc(
    by_province: list[dict[str, Any]],
    *,
    regional: dict[str, Any] | None = None,
    as_of_siar: str | None = None,
) -> dict[str, Any]:
    """ETc por cultivo representativo a partir de ET0 SiAR y Kc de referencia."""
    out = _empty()
    out["as_of_siar"] = as_of_siar
    out["kc_table"] = [
        {
            "crop_id": c["id"],
            "name_es": c["name_es"],
            "name_en": c["name_en"],
            "kc": c["kc"],
            "source_es": c["source_es"],
        }
        for c in CROPS
    ]
    out["crops_meta"] = out["kc_table"]
    out["caveats_es"] = [
        "No usamos dotaciones ni restricciones oficiales de la Junta: no están en la app.",
        "La comparación con el embalse reparte el volumen usable entre todas las hectáreas de regadío (proxy).",
        "ETc_7d es 7 × el día SiAR (estimación lineal), no un balance de suelo.",
        "Si toda la provincia fuera un solo cultivo, la demanda hm³ es solo un qué-pasaría.",
    ]

    if not by_province:
        out["note_es"] = "Sin provincias con ET0 SiAR para estimar necesidades por cultivo."
        return out

    packed: list[dict[str, Any]] = []
    for p in by_province:
        name = str(p.get("province_name") or "")
        if not name or name == "Andalucía":
            continue
        et0 = p.get("et0_mm")
        if et0 is None:
            continue
        ha = int(p.get("irrigated_ha") or 0)
        if ha <= 0:
            continue
        packed.append(
            _pack_scope(
                province_name=name,
                et0_mm=float(et0),
                pe_mm=float(p.get("pe_mm") or 0),
                irrigated_ha=ha,
                stored_hm3=(
                    float(p["stored_hm3"]) if p.get("stored_hm3") is not None else None
                ),
                baseline_kc=float(p.get("kc") or DEFAULT_KC),
                baseline_demand_hm3=(
                    float(p["daily_demand_hm3"])
                    if p.get("daily_demand_hm3") is not None
                    else None
                ),
                days_autonomy=(
                    float(p["days_autonomy"])
                    if p.get("days_autonomy") is not None
                    else None
                ),
                burn_hm3_per_day=(
                    float(p["storage_burn_hm3_per_day"])
                    if p.get("storage_burn_hm3_per_day") is not None
                    else None
                ),
            )
        )

    if not packed:
        out["note_es"] = "Sin filas provinciales válidas para ETc."
        return out

    out["by_province"] = packed
    out["available"] = True

    if regional and regional.get("et0_mm") is not None and regional.get("irrigated_ha"):
        out["regional"] = _pack_scope(
            province_name="Andalucía",
            et0_mm=float(regional["et0_mm"]),
            pe_mm=float(regional.get("pe_mm") or 0),
            irrigated_ha=int(regional["irrigated_ha"]),
            stored_hm3=(
                float(regional["stored_hm3"])
                if regional.get("stored_hm3") is not None
                else None
            ),
            baseline_kc=float(regional.get("kc") or DEFAULT_KC),
            baseline_demand_hm3=(
                float(regional["daily_demand_hm3"])
                if regional.get("daily_demand_hm3") is not None
                else None
            ),
            days_autonomy=(
                float(regional["days_autonomy"])
                if regional.get("days_autonomy") is not None
                else None
            ),
            burn_hm3_per_day=(
                float(regional["storage_burn_hm3_per_day"])
                if regional.get("storage_burn_hm3_per_day") is not None
                else None
            ),
        )
    else:
        # Weighted regional fallback from packed provinces
        ha_tot = sum(int(p["irrigated_ha"]) for p in packed)
        if ha_tot > 0:
            et0_w = sum(float(p["et0_mm"]) * int(p["irrigated_ha"]) for p in packed) / ha_tot
            pe_w = sum(float(p["pe_mm"] or 0) * int(p["irrigated_ha"]) for p in packed) / ha_tot
            kc_w = sum(float(p["baseline_kc"]) * int(p["irrigated_ha"]) for p in packed) / ha_tot
            stored = sum(float(p["stored_hm3"] or 0) for p in packed if p.get("stored_hm3") is not None)
            out["regional"] = _pack_scope(
                province_name="Andalucía",
                et0_mm=et0_w,
                pe_mm=pe_w,
                irrigated_ha=ha_tot,
                stored_hm3=stored if stored else None,
                baseline_kc=kc_w,
                baseline_demand_hm3=None,
                days_autonomy=None,
                burn_hm3_per_day=None,
            )

    out["note_es"] = (
        "Necesidad del cultivo (ETc) = coeficiente Kc × evaporación SiAR (ET0). "
        "Comparamos con un proxy de agua embalsada repartida por hectárea de regadío "
        "y con la demanda base ya usada en autonomía — no son dotaciones oficiales."
    )
    return out
