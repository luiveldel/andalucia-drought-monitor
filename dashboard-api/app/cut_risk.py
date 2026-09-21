"""Composite «Riesgo de corte» 0–100 from existing irrigation / climate signals.

Transparent, explainable weights. Missing signals are dropped and remaining
weights are renormalized — we never invent inputs.
"""

from __future__ import annotations

from typing import Any

# Keep in sync with irrigation_autonomy.THRESHOLDS (avoid importing sqlalchemy here).
THRESHOLDS = {
    "autonomy_critical": 21.0,
    "autonomy_warning": 60.0,
    "autonomy_watch": 90.0,
}


def _f(v, nd: int = 2):
    if v is None:
        return None
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


# Nominal weights when every driver is present. Sum = 1.0.
WEIGHTS = {
    "fill": 0.25,  # reservoir fill / stock
    "autonomy": 0.30,  # days of usable autonomy
    "until_critical": 0.20,  # calendar days until autonomy < critical
    "burn": 0.15,  # burn vs SiAR demand (+ deficit intensity)
    "climate": 0.10,  # SPI and/or heat×demand stress
}

BANDS = {
    "ok": (0.0, 25.0),
    "watch": (25.0, 50.0),
    "warning": (50.0, 75.0),
    "critical": (75.0, 100.0),
}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _band(score: float) -> str:
    if score >= BANDS["critical"][0]:
        return "critical"
    if score >= BANDS["warning"][0]:
        return "warning"
    if score >= BANDS["watch"][0]:
        return "watch"
    return "ok"


def _score_fill(fill_pct: float | None) -> tuple[float | None, str]:
    if fill_pct is None:
        return None, "Sin dato de llenado."
    s = _clamp(100.0 - float(fill_pct))
    return s, f"Llenado {float(fill_pct):.0f}% → riesgo stock {s:.0f}."


def _score_autonomy(days: float | None) -> tuple[float | None, str]:
    if days is None:
        return None, "Sin días de autonomía."
    d = float(days)
    crit = float(THRESHOLDS["autonomy_critical"])
    warn = float(THRESHOLDS["autonomy_warning"])
    watch = float(THRESHOLDS["autonomy_watch"])
    if d <= crit:
        s = 100.0
    elif d <= warn:
        # crit→100 … warn→55
        s = 100.0 - (d - crit) / (warn - crit) * 45.0
    elif d <= watch:
        # warn→55 … watch→25
        s = 55.0 - (d - warn) / (watch - warn) * 30.0
    else:
        # watch→25 … 180d→0
        s = 25.0 * max(0.0, 1.0 - (d - watch) / (180.0 - watch))
    s = _clamp(s)
    return s, f"Autonomía {d:.0f} d (crítico <{crit:.0f}) → {s:.0f}."


def _score_until(until: int | float | None) -> tuple[float | None, str]:
    if until is None:
        # Comfortable at +horizon: treat as low pressure, not "missing"
        return 8.0, "Sin fecha crítica en el horizonte proyectado → presión baja."
    try:
        u = int(until)
    except (TypeError, ValueError):
        return None, "Sin proyección hasta crítico."
    if u <= 0:
        s = 100.0
    elif u <= 7:
        s = 100.0 - (u / 7.0) * 25.0  # 100→75
    elif u <= 21:
        s = 75.0 - ((u - 7) / 14.0) * 35.0  # 75→40
    else:
        s = 40.0 - min(30.0, (u - 21) / 40.0 * 30.0)  # →≥10
    s = _clamp(s)
    return s, f"~{u} d de calendario hasta crítico → {s:.0f}."


def _score_burn(
    ratio: float | None,
    deficit_7d: float | None,
    daily_demand: float | None,
) -> tuple[float | None, str]:
    parts: list[float] = []
    notes: list[str] = []
    if ratio is not None:
        r = float(ratio)
        # 1.0 → 25, 1.25 → 55, 2.0 → 100
        if r <= 1.0:
            sr = 25.0 * r
        elif r <= 1.25:
            sr = 25.0 + (r - 1.0) / 0.25 * 30.0
        elif r <= 2.0:
            sr = 55.0 + (r - 1.25) / 0.75 * 45.0
        else:
            sr = 100.0
        parts.append(_clamp(sr))
        notes.append(f"quemado/demanda ×{r:.2f}")
    if deficit_7d is not None and daily_demand is not None and float(daily_demand) > 1e-9:
        # how many days of demand the 7d deficit covers
        intensity = float(deficit_7d) / (float(daily_demand) * 7.0)
        # 0.5 → 20, 1.0 → 55, 1.5+ → 90
        sd = _clamp(20.0 + intensity * 50.0)
        parts.append(sd)
        notes.append(f"déficit 7d {float(deficit_7d):.1f} hm³")
    if not parts:
        return None, "Sin burn ni déficit SiAR."
    s = sum(parts) / len(parts)
    return s, (" · ".join(notes) + f" → {s:.0f}.")


def _score_climate(
    spi: float | None,
    heat_lift_pct: float | None,
    latest_is_heat: bool | None,
) -> tuple[float | None, str]:
    parts: list[float] = []
    notes: list[str] = []
    if spi is not None:
        # SPI 0 → 0, −1 → 50, −1.5 → 75, ≤−2 → 100
        v = float(spi)
        if v >= 0:
            ss = 0.0
        elif v >= -1.0:
            ss = (-v) * 50.0
        elif v >= -1.5:
            ss = 50.0 + (-v - 1.0) / 0.5 * 25.0
        else:
            ss = 75.0 + min(25.0, (-v - 1.5) / 0.5 * 25.0)
        parts.append(_clamp(ss))
        notes.append(f"SPI {v:.2f}")
    if heat_lift_pct is not None:
        # lift 0% → 10, 20% → 50, 40%+ → 90
        hl = float(heat_lift_pct)
        sh = _clamp(10.0 + hl * 2.0)
        parts.append(sh)
        notes.append(f"demanda en calor +{hl:.0f}%")
    elif latest_is_heat is True:
        parts.append(55.0)
        notes.append("día de calor reciente")
    if not parts:
        return None, "Sin SPI ni señal de calor."
    s = sum(parts) / len(parts)
    return s, (" · ".join(notes) + f" → {s:.0f}.")


def _combine(
    drivers_raw: dict[str, tuple[float | None, str]],
) -> dict[str, Any]:
    available = {k: v for k, v in drivers_raw.items() if v[0] is not None}
    if not available:
        return {
            "available": False,
            "score": None,
            "band": "unknown",
            "weights_used": {},
            "drivers": [],
            "why_es": "No hay señales suficientes para calcular el riesgo de corte.",
        }
    w_sum = sum(WEIGHTS[k] for k in available)
    weights_used = {k: round(WEIGHTS[k] / w_sum, 3) for k in available}
    score = 0.0
    drivers: list[dict[str, Any]] = []
    for k, (val, explain) in available.items():
        assert val is not None
        w = weights_used[k]
        contrib = w * val
        score += contrib
        drivers.append(
            {
                "id": k,
                "label_es": {
                    "fill": "Llenado embalse",
                    "autonomy": "Días de autonomía",
                    "until_critical": "Días hasta crítico",
                    "burn": "Quemado / déficit SiAR",
                    "climate": "SPI / calor",
                }.get(k, k),
                "score": _f(val, 1),
                "weight": w,
                "contribution": _f(contrib, 1),
                "explain_es": explain,
            }
        )
    drivers.sort(key=lambda d: float(d["contribution"] or 0), reverse=True)
    score_r = _f(score, 1)
    band = _band(float(score_r or 0))
    top = drivers[0] if drivers else None
    why = (
        f"Nota {score_r:.0f}/100 ({band}). "
        f"Pesa más: {top['label_es']} ({top['contribution']:.0f} pts). "
        "Pesos transparentes; se recalculan si falta algún dato."
        if top and score_r is not None
        else "Sin desglose."
    )
    return {
        "available": True,
        "score": score_r,
        "band": band,
        "weights_nominal": dict(WEIGHTS),
        "weights_used": weights_used,
        "drivers": drivers,
        "why_es": why,
        "bands": {
            "ok": "<25 · situación cómoda",
            "watch": "25–49 · vigilancia",
            "warning": "50–74 · planificar restricciones",
            "critical": "≥75 · riesgo alto de corte",
        },
    }


def score_province(
    *,
    province_name: str,
    fill_pct: float | None,
    days_autonomy: float | None,
    days_until_critical: int | float | None,
    burn_vs_demand_ratio: float | None,
    deficit_7d_hm3: float | None,
    daily_demand_hm3: float | None,
    spi_value: float | None = None,
    heat_lift_pct: float | None = None,
    latest_is_heat: bool | None = None,
) -> dict[str, Any]:
    raw = {
        "fill": _score_fill(fill_pct),
        "autonomy": _score_autonomy(days_autonomy),
        "until_critical": _score_until(days_until_critical),
        "burn": _score_burn(burn_vs_demand_ratio, deficit_7d_hm3, daily_demand_hm3),
        "climate": _score_climate(spi_value, heat_lift_pct, latest_is_heat),
    }
    out = _combine(raw)
    out["province_name"] = province_name
    out["inputs"] = {
        "fill_pct": _f(fill_pct, 1) if fill_pct is not None else None,
        "days_autonomy": _f(days_autonomy, 1) if days_autonomy is not None else None,
        "days_until_critical": (
            int(days_until_critical) if days_until_critical is not None else None
        ),
        "burn_vs_demand_ratio": (
            _f(burn_vs_demand_ratio, 2) if burn_vs_demand_ratio is not None else None
        ),
        "deficit_7d_hm3": _f(deficit_7d_hm3, 3) if deficit_7d_hm3 is not None else None,
        "spi_value": _f(spi_value, 3) if spi_value is not None else None,
        "heat_lift_pct": _f(heat_lift_pct, 1) if heat_lift_pct is not None else None,
    }
    return out


def build_cut_risk(
    *,
    regional: dict[str, Any] | None,
    by_province: list[dict[str, Any]],
    projection: dict[str, Any] | None,
    heat_demand_cross: dict[str, Any] | None = None,
    spi: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Regional + per-province cut-risk scores from already-computed signals."""
    empty = {
        "available": False,
        "note_es": "Sin datos de autonomía de riego para el riesgo de corte.",
        "method_es": (
            "Índice 0–100 a partir de llenado, autonomía, días hasta crítico, "
            "quemado/déficit SiAR y, si hay, SPI o estrés por calor. "
            f"Pesos nominales: llenado {WEIGHTS['fill']:.0%}, autonomía {WEIGHTS['autonomy']:.0%}, "
            f"hasta crítico {WEIGHTS['until_critical']:.0%}, quemado {WEIGHTS['burn']:.0%}, "
            f"clima {WEIGHTS['climate']:.0%}."
        ),
        "weights_nominal": dict(WEIGHTS),
        "bands": {
            "ok": "<25",
            "watch": "25–49",
            "warning": "50–74",
            "critical": "≥75",
        },
        "regional": None,
        "by_province": [],
    }
    if not by_province and not regional:
        return empty

    proj_by = {
        str(p.get("province_name") or ""): p
        for p in (projection or {}).get("by_province") or []
    }
    heat_by = {
        str(p.get("province_name") or ""): p
        for p in (heat_demand_cross or {}).get("by_province") or []
    }
    spi_by = {
        str(p.get("province_name") or ""): p.get("spi_value")
        for p in (spi or {}).get("provinces") or []
    }
    regional_spi = (spi or {}).get("regional_spi")
    heat_reg = (heat_demand_cross or {}).get("regional") or {}

    scored: list[dict[str, Any]] = []
    for p in by_province:
        name = str(p.get("province_name") or "")
        if name == "Andalucía":
            continue
        pr = proj_by.get(name) or {}
        ht = heat_by.get(name) or {}
        scored.append(
            score_province(
                province_name=name,
                fill_pct=p.get("fill_pct"),
                days_autonomy=p.get("days_autonomy"),
                days_until_critical=pr.get("days_until_critical"),
                burn_vs_demand_ratio=p.get("burn_vs_demand_ratio"),
                deficit_7d_hm3=p.get("deficit_7d_hm3"),
                daily_demand_hm3=p.get("daily_demand_hm3"),
                spi_value=spi_by.get(name),
                heat_lift_pct=ht.get("demand_lift_pct"),
                latest_is_heat=ht.get("latest_is_heat"),
            )
        )
    scored.sort(
        key=lambda r: (
            -(float(r["score"]) if r.get("score") is not None else -1),
            r.get("province_name") or "",
        )
    )

    regional_out = None
    if regional:
        proj_r = (projection or {}).get("regional") or {}
        regional_out = score_province(
            province_name="Andalucía",
            fill_pct=regional.get("fill_pct"),
            days_autonomy=regional.get("days_autonomy"),
            days_until_critical=proj_r.get("days_until_critical"),
            burn_vs_demand_ratio=regional.get("burn_vs_demand_ratio"),
            deficit_7d_hm3=regional.get("deficit_7d_hm3"),
            daily_demand_hm3=regional.get("daily_demand_hm3"),
            spi_value=float(regional_spi) if regional_spi is not None else None,
            heat_lift_pct=heat_reg.get("demand_lift_pct"),
            latest_is_heat=heat_reg.get("latest_is_heat"),
        )

    return {
        "available": bool(scored or (regional_out and regional_out.get("available"))),
        "note_es": (
            "Piloto orientativo: no sustituye la mesa de sequía ni los decretos de "
            "restricción. Combina señales que ya ves en Riego y Clima."
        ),
        "method_es": empty["method_es"],
        "weights_nominal": dict(WEIGHTS),
        "bands": empty["bands"],
        "regional": regional_out,
        "by_province": scored,
    }
