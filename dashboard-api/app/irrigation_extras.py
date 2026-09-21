"""Extras for irrigation tab: 7d autonomy projection + RIA vs SiAR compare."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.irrigation_autonomy import (
    DEFAULT_KC,
    IRRIGATED_HA_2023,
    KC_BY_PROVINCE,
    THRESHOLDS,
    _daily_demand_hm3,
    _f,
    _risk_level,
)
from app.provinces_meta import PROVINCES
from app.meteo_forecast import OM_LAT as _OM_LAT, OM_LON as _OM_LON

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 30 * 60

CRITICAL_AUTONOMY_DAYS = float(THRESHOLDS["autonomy_critical"])


def _days_until_critical(
    days_autonomy_start: float | None,
    series: list[dict[str, Any]],
    threshold: float = CRITICAL_AUTONOMY_DAYS,
) -> int | None:
    """Calendar days until projected autonomy falls below threshold (0 = already).

    Extrapolates past the forecast horizon only when +horizon autonomy is already
    in the warning band (avoids false alarms from short steep drops on high stock).
    """
    if days_autonomy_start is not None and float(days_autonomy_start) < threshold:
        return 0
    for i, day in enumerate(series):
        da = day.get("days_autonomy")
        if da is not None and float(da) < threshold:
            return i + 1  # after that many forecast days
    # beyond horizon: only if end-of-horizon is already in warning band
    warn_band = float(THRESHOLDS.get("autonomy_warning", 60.0))
    if len(series) >= 2 and days_autonomy_start is not None:
        start = float(days_autonomy_start)
        end = series[-1].get("days_autonomy")
        if end is not None:
            end_f = float(end)
            if end_f >= warn_band:
                return None  # still comfortable at +horizon
            drop = start - end_f
            if drop > 0.5:
                per_day = drop / len(series)
                remain = start - threshold
                if per_day > 1e-9:
                    est = int(remain / per_day + 0.999)
                    return max(len(series) + 1, est) if start >= threshold else 0
    return None



def _rows(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params)
    return [dict(row._mapping) for row in result]


def _om_et0_forecast(lat: float, lon: float, days: int = 7) -> list[dict[str, Any]]:
    key = f"{lat:.3f},{lon:.3f}:{days}"
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Europe/Madrid",
        "forecast_days": days,
        "daily": "et0_fao_evapotranspiration,precipitation_sum",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": "andalucia-drought-monitor/1.0"}
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    daily = raw.get("daily") or {}
    times = daily.get("time") or []
    et0s = daily.get("et0_fao_evapotranspiration") or []
    precs = daily.get("precipitation_sum") or []
    out: list[dict[str, Any]] = []
    for i, d in enumerate(times):
        et0 = et0s[i] if i < len(et0s) else None
        pe = precs[i] if i < len(precs) else 0.0
        if et0 is None:
            continue
        out.append(
            {
                "date": d,
                "et0_mm": float(et0),
                "precip_mm": float(pe or 0),
            }
        )
    _cache[key] = (now, out)
    return out


def build_autonomy_projection(
    by_province: list[dict[str, Any]],
    *,
    horizon_days: int = 7,
) -> dict[str, Any]:
    """Project usable storage forward using Open-Meteo FAO ET0 + precip."""
    empty = {
        "available": False,
        "horizon_days": horizon_days,
        "source": "Open-Meteo ET0 FAO-56",
        "attribution": "https://open-meteo.com",
        "note": "",
        "regional": None,
        "by_province": [],
    }
    if not by_province:
        empty["note"] = "Sin provincias base para proyectar."
        return empty

    coords = {p["name"]: (float(p["lat"]), float(p["lon"])) for p in PROVINCES}
    projected: list[dict[str, Any]] = []

    for base in by_province:
        name = base["province_name"]
        if name == "Andalucía":
            continue
        lat, lon = coords.get(name, (_OM_LAT, _OM_LON))
        try:
            days_fc = _om_et0_forecast(lat, lon, horizon_days)
        except Exception as exc:  # noqa: BLE001
            projected.append(
                {
                    "province_name": name,
                    "available": False,
                    "error": str(exc)[:160],
                    "days": [],
                }
            )
            continue
        if not days_fc:
            continue
        kc = float(base.get("kc") or KC_BY_PROVINCE.get(name, DEFAULT_KC))
        ha = int(base.get("irrigated_ha") or IRRIGATED_HA_2023.get(name, 0))
        stored = float(base.get("stored_hm3") or 0)
        series: list[dict[str, Any]] = []
        cum_demand = 0.0
        for day in days_fc:
            dem = _daily_demand_hm3(day["et0_mm"], day["precip_mm"], ha, kc)
            stored = max(0.0, stored - dem)
            cum_demand += dem
            days_aut = (stored / dem) if dem > 1e-9 else None
            series.append(
                {
                    "date": day["date"],
                    "et0_mm": _f(day["et0_mm"], 2),
                    "precip_mm": _f(day["precip_mm"], 2),
                    "daily_demand_hm3": _f(dem, 3),
                    "stored_hm3": _f(stored, 1),
                    "days_autonomy": _f(days_aut, 1) if days_aut is not None else None,
                }
            )
        end_days = series[-1]["days_autonomy"] if series else None
        start_days = base.get("days_autonomy")
        until_crit = _days_until_critical(
            float(start_days) if start_days is not None else None,
            series,
        )
        projected.append(
            {
                "province_name": name,
                "available": True,
                "kc": _f(kc, 2),
                "irrigated_ha": ha,
                "stored_start_hm3": base.get("stored_hm3"),
                "stored_end_hm3": series[-1]["stored_hm3"] if series else None,
                "cumulative_demand_hm3": _f(cum_demand, 3),
                "days_autonomy_start": start_days,
                "days_autonomy_end": end_days,
                "days_until_critical": until_crit,
                "critical_threshold_days": CRITICAL_AUTONOMY_DAYS,
                "risk_level_end": _risk_level(
                    float(end_days) if end_days is not None else None
                ),
                "days": series,
            }
        )

    # Regional: sum storage and demand day-aligned
    regional = None
    if projected and all(p.get("available") for p in projected):
        # use dates from first province
        dates = [d["date"] for d in projected[0].get("days") or []]
        series_r: list[dict[str, Any]] = []
        stored0 = sum(float(p.get("stored_start_hm3") or 0) for p in projected)
        stored = stored0
        cum = 0.0
        for i, d in enumerate(dates):
            dem = 0.0
            et0_w = 0.0
            pe_w = 0.0
            ha_t = 0
            for p in projected:
                day = (p.get("days") or [None])[i]
                if not day:
                    continue
                dem += float(day["daily_demand_hm3"] or 0)
                ha_p = int(p.get("irrigated_ha") or 0)
                et0_w += float(day["et0_mm"] or 0) * ha_p
                pe_w += float(day["precip_mm"] or 0) * ha_p
                ha_t += ha_p
            stored = max(0.0, stored - dem)
            cum += dem
            days_aut = (stored / dem) if dem > 1e-9 else None
            series_r.append(
                {
                    "date": d,
                    "et0_mm": _f(et0_w / ha_t, 2) if ha_t else None,
                    "precip_mm": _f(pe_w / ha_t, 2) if ha_t else None,
                    "daily_demand_hm3": _f(dem, 3),
                    "stored_hm3": _f(stored, 1),
                    "days_autonomy": _f(days_aut, 1) if days_aut is not None else None,
                }
            )
        end_days = series_r[-1]["days_autonomy"] if series_r else None
        # regional start filled later by caller; compute until_crit from series only
        until_crit = _days_until_critical(None, series_r)
        # if first projected day already critical
        if series_r and series_r[0].get("days_autonomy") is not None:
            if float(series_r[0]["days_autonomy"]) < CRITICAL_AUTONOMY_DAYS:
                until_crit = 0
        regional = {
            "province_name": "Andalucía",
            "available": True,
            "stored_start_hm3": _f(stored0, 1),
            "stored_end_hm3": series_r[-1]["stored_hm3"] if series_r else None,
            "cumulative_demand_hm3": _f(cum, 3),
            "days_autonomy_start": None,
            "days_autonomy_end": end_days,
            "days_until_critical": until_crit,
            "critical_threshold_days": CRITICAL_AUTONOMY_DAYS,
            "risk_level_end": _risk_level(
                float(end_days) if end_days is not None else None
            ),
            "days": series_r,
        }

    return {
        "available": bool(projected),
        "horizon_days": horizon_days,
        "source": "Open-Meteo ET0 FAO-56 (+ precip)",
        "attribution": "https://open-meteo.com",
        "note": (
            "Proyección piloto: parte del embalse usable actual y resta cada día "
            "Kc×max(0, ET0_OM − precip_OM)×ha. No es un balance de derechos ni AEMET ET0 "
            "(AEMET no publica ET0 en el municipio; usamos Open-Meteo FAO-56)."
        ),
        "regional": regional,
        "by_province": projected,
    }



# Open-Meteo free forecast typically covers ~16 days; beyond that we only
# extend with the mean of the observed forecast window (clearly labelled).
_OM_MAX_FORECAST_DAYS = 16
_SCENARIO_HORIZONS = (7, 14, 21)
_DRY_ET0_FACTOR = 1.15  # pessimistic: ET0 +15% vs forecast, precip = 0


def _extend_forecast(days_fc: list[dict[str, Any]], horizon: int) -> tuple[list[dict[str, Any]], bool]:
    """Return forecast sliced/extended to horizon. Second flag = used mean extrapolation."""
    if not days_fc:
        return [], False
    if len(days_fc) >= horizon:
        return days_fc[:horizon], False
    # Extrapolate remaining days with mean ET0 / precip of the OM window.
    mean_et0 = sum(d["et0_mm"] for d in days_fc) / len(days_fc)
    mean_pe = sum(d["precip_mm"] for d in days_fc) / len(days_fc)
    from datetime import date, timedelta

    last = date.fromisoformat(str(days_fc[-1]["date"])[:10])
    out = list(days_fc)
    for i in range(len(days_fc), horizon):
        last = last + timedelta(days=1)
        out.append({"date": last.isoformat(), "et0_mm": mean_et0, "precip_mm": mean_pe})
    return out, True


def _apply_scenario_mode(
    days_fc: list[dict[str, Any]], mode: str
) -> list[dict[str, Any]]:
    if mode == "baseline":
        return [
            {"date": d["date"], "et0_mm": d["et0_mm"], "precip_mm": d["precip_mm"]}
            for d in days_fc
        ]
    # dry_high_et0: no rain + elevated ET0
    return [
        {
            "date": d["date"],
            "et0_mm": float(d["et0_mm"]) * _DRY_ET0_FACTOR,
            "precip_mm": 0.0,
        }
        for d in days_fc
    ]


def _project_from_forecast(
    base: dict[str, Any],
    days_fc: list[dict[str, Any]],
) -> dict[str, Any]:
    name = base["province_name"]
    kc = float(base.get("kc") or KC_BY_PROVINCE.get(name, DEFAULT_KC))
    ha = int(base.get("irrigated_ha") or IRRIGATED_HA_2023.get(name, 0))
    stored = float(base.get("stored_hm3") or 0)
    series: list[dict[str, Any]] = []
    cum_demand = 0.0
    for day in days_fc:
        dem = _daily_demand_hm3(day["et0_mm"], day["precip_mm"], ha, kc)
        stored = max(0.0, stored - dem)
        cum_demand += dem
        days_aut = (stored / dem) if dem > 1e-9 else None
        series.append(
            {
                "date": day["date"],
                "et0_mm": _f(day["et0_mm"], 2),
                "precip_mm": _f(day["precip_mm"], 2),
                "daily_demand_hm3": _f(dem, 3),
                "stored_hm3": _f(stored, 1),
                "days_autonomy": _f(days_aut, 1) if days_aut is not None else None,
            }
        )
    end_days = series[-1]["days_autonomy"] if series else None
    start_days = base.get("days_autonomy")
    until_crit = _days_until_critical(
        float(start_days) if start_days is not None else None,
        series,
    )
    # Estimated calendar date of critical / restriction (warning band)
    crit_date = None
    restrict_date = None
    warn_band = float(THRESHOLDS.get("autonomy_warning", 60.0))
    if until_crit is not None and until_crit > 0 and series:
        from datetime import date, timedelta

        start_d = date.fromisoformat(str(series[0]["date"])[:10])
        # until_crit is "after N forecast days" → date of that day
        crit_date = (start_d + timedelta(days=until_crit - 1)).isoformat()
    elif until_crit == 0:
        crit_date = series[0]["date"] if series else None
    for i, day in enumerate(series):
        da = day.get("days_autonomy")
        if da is not None and float(da) < warn_band:
            restrict_date = day["date"]
            break
    if start_days is not None and float(start_days) < warn_band:
        restrict_date = series[0]["date"] if series else restrict_date

    return {
        "province_name": name,
        "available": True,
        "kc": _f(kc, 2),
        "irrigated_ha": ha,
        "stored_start_hm3": base.get("stored_hm3"),
        "stored_end_hm3": series[-1]["stored_hm3"] if series else None,
        "fill_pct_start": base.get("fill_pct"),
        "cumulative_demand_hm3": _f(cum_demand, 3),
        "days_autonomy_start": start_days,
        "days_autonomy_end": end_days,
        "days_until_critical": until_crit,
        "critical_date": crit_date,
        "restriction_date": restrict_date,
        "critical_threshold_days": CRITICAL_AUTONOMY_DAYS,
        "risk_level_end": _risk_level(float(end_days) if end_days is not None else None),
        "days": series,
    }


def _regional_from_projected(
    projected: list[dict[str, Any]],
    *,
    regional_start_days: float | None = None,
) -> dict[str, Any] | None:
    ok = [p for p in projected if p.get("available")]
    if not ok:
        return None
    dates = [d["date"] for d in (ok[0].get("days") or [])]
    if not dates:
        return None
    series_r: list[dict[str, Any]] = []
    stored0 = sum(float(p.get("stored_start_hm3") or 0) for p in ok)
    stored = stored0
    cum = 0.0
    for i, d in enumerate(dates):
        dem = 0.0
        et0_w = 0.0
        pe_w = 0.0
        ha_t = 0
        for p in ok:
            day = (p.get("days") or [None])[i]
            if not day:
                continue
            dem += float(day["daily_demand_hm3"] or 0)
            ha_p = int(p.get("irrigated_ha") or 0)
            et0_w += float(day["et0_mm"] or 0) * ha_p
            pe_w += float(day["precip_mm"] or 0) * ha_p
            ha_t += ha_p
        stored = max(0.0, stored - dem)
        cum += dem
        days_aut = (stored / dem) if dem > 1e-9 else None
        series_r.append(
            {
                "date": d,
                "et0_mm": _f(et0_w / ha_t, 2) if ha_t else None,
                "precip_mm": _f(pe_w / ha_t, 2) if ha_t else None,
                "daily_demand_hm3": _f(dem, 3),
                "stored_hm3": _f(stored, 1),
                "days_autonomy": _f(days_aut, 1) if days_aut is not None else None,
            }
        )
    end_days = series_r[-1]["days_autonomy"] if series_r else None
    until_crit = _days_until_critical(
        float(regional_start_days) if regional_start_days is not None else None,
        series_r,
    )
    crit_date = None
    restrict_date = None
    warn_band = float(THRESHOLDS.get("autonomy_warning", 60.0))
    if until_crit is not None and until_crit > 0 and series_r:
        from datetime import date, timedelta

        start_d = date.fromisoformat(str(series_r[0]["date"])[:10])
        crit_date = (start_d + timedelta(days=until_crit - 1)).isoformat()
    elif until_crit == 0:
        crit_date = series_r[0]["date"] if series_r else None
    for day in series_r:
        da = day.get("days_autonomy")
        if da is not None and float(da) < warn_band:
            restrict_date = day["date"]
            break
    return {
        "province_name": "Andalucía",
        "available": True,
        "stored_start_hm3": _f(stored0, 1),
        "stored_end_hm3": series_r[-1]["stored_hm3"] if series_r else None,
        "cumulative_demand_hm3": _f(cum, 3),
        "days_autonomy_start": regional_start_days,
        "days_autonomy_end": end_days,
        "days_until_critical": until_crit,
        "critical_date": crit_date,
        "restriction_date": restrict_date,
        "critical_threshold_days": CRITICAL_AUTONOMY_DAYS,
        "risk_level_end": _risk_level(float(end_days) if end_days is not None else None),
        "days": series_r,
    }


def build_irrigation_scenarios(
    by_province: list[dict[str, Any]],
    *,
    regional: dict[str, Any] | None = None,
    horizons: tuple[int, ...] = _SCENARIO_HORIZONS,
) -> dict[str, Any]:
    """Baseline Open-Meteo forecast vs dry/high-ET0 pessimistic scenarios.

    Horizons 7/14 use Open-Meteo directly (up to ~16 d). Horizon 21 may extend
    the last OM days with their mean ET0/precip — labelled in caveats_es.
    """
    empty = {
        "available": False,
        "modes": [
            {
                "id": "baseline",
                "label_es": "Pronóstico",
                "describe_es": "ET0 y lluvia del pronóstico Open-Meteo (FAO-56).",
            },
            {
                "id": "dry_high_et0",
                "label_es": "Seco / ET0 alta",
                "describe_es": (
                    f"Sin lluvia y ET0 un {_DRY_ET0_FACTOR:.0%} del pronóstico "
                    "(escenario pesimista orientativo)."
                ),
            },
        ],
        "horizons": list(horizons),
        "note_es": "",
        "caveats_es": [],
        "attribution": "https://open-meteo.com",
        "by_mode": {},
    }
    if not by_province:
        empty["note_es"] = "Sin provincias base para escenarios."
        return empty

    coords = {p["name"]: (float(p["lat"]), float(p["lon"])) for p in PROVINCES}
    max_h = max(horizons)
    fetch_days = min(max_h, _OM_MAX_FORECAST_DAYS)

    # Prefetch once per province (cached).
    forecasts: dict[str, list[dict[str, Any]]] = {}
    errors: dict[str, str] = {}
    for base in by_province:
        name = base["province_name"]
        if name == "Andalucía":
            continue
        lat, lon = coords.get(name, (_OM_LAT, _OM_LON))
        try:
            forecasts[name] = _om_et0_forecast(lat, lon, fetch_days)
        except Exception as exc:  # noqa: BLE001
            errors[name] = str(exc)[:160]

    if not forecasts:
        empty["note_es"] = "No se pudo obtener el pronóstico Open-Meteo."
        return empty

    caveats: list[str] = [
        "Escenarios piloto: no son un balance oficial de derechos ni un aviso de la Junta.",
        "Parten del embalse usable actual y restan cada día la demanda Kc×max(0, ET0−P)×ha.",
    ]
    if max_h > _OM_MAX_FORECAST_DAYS:
        caveats.append(
            f"Open-Meteo cubre ~{_OM_MAX_FORECAST_DAYS} d; el horizonte {max_h} d "
            "extiende con la media de ET0/lluvia del tramo pronosticado (no es un "
            "pronóstico real día a día)."
        )
    caveats.append(
        f"El modo seco aplica precipitación 0 y ET0 ×{_DRY_ET0_FACTOR:.2f} "
        "sobre el mismo tramo meteorológico."
    )

    regional_start = (regional or {}).get("days_autonomy")
    by_mode: dict[str, Any] = {}
    for mode in ("baseline", "dry_high_et0"):
        by_horizon: dict[str, Any] = {}
        for horizon in horizons:
            projected: list[dict[str, Any]] = []
            used_ext = False
            for base in by_province:
                name = base["province_name"]
                if name == "Andalucía":
                    continue
                if name in errors:
                    projected.append(
                        {
                            "province_name": name,
                            "available": False,
                            "error": errors[name],
                            "days": [],
                        }
                    )
                    continue
                raw = forecasts.get(name) or []
                extended, was_ext = _extend_forecast(raw, horizon)
                used_ext = used_ext or was_ext
                days_fc = _apply_scenario_mode(extended, mode)
                if not days_fc:
                    continue
                projected.append(_project_from_forecast(base, days_fc))
            regional_row = _regional_from_projected(
                projected, regional_start_days=float(regional_start) if regional_start is not None else None
            )
            by_horizon[str(horizon)] = {
                "available": bool(any(p.get("available") for p in projected)),
                "horizon_days": horizon,
                "mode": mode,
                "extrapolated_beyond_om": used_ext,
                "regional": regional_row,
                "by_province": projected,
            }
        by_mode[mode] = by_horizon

    return {
        "available": True,
        "modes": empty["modes"],
        "horizons": list(horizons),
        "note_es": (
            "Compara el pronóstico meteorológico con un escenario seco de ET0 alta "
            "para anticipar cuándo la autonomía podría entrar en alerta o crítico."
        ),
        "caveats_es": caveats,
        "attribution": "https://open-meteo.com",
        "source": "Open-Meteo ET0 FAO-56",
        "by_mode": by_mode,
    }



def build_ria_siar_compare(conn: Connection, as_of: str | None = None) -> dict[str, Any]:
    """Side-by-side RIA vs SiAR provincial means for the latest common date.

    SiAR can publish one day ahead of RIA. When the caller passes a SiAR-only
    max date, we fall back to the latest date present in BOTH networks.
    """
    empty = {
        "available": False,
        "as_of": None,
        "note": "",
        "regional": None,
        "by_province": [],
    }
    try:
        common_rows = _rows(
            conn,
            """
            SELECT LEAST(
                (SELECT MAX(fecha) FROM raw.raw_siar_clima_diario WHERE ccaa_codigo='AND'),
                (SELECT MAX(fecha) FROM raw.raw_ria_clima_diario)
            )::text AS d
            """,
        )
        common = common_rows[0]["d"] if common_rows and common_rows[0].get("d") else None
        if not common:
            empty["note"] = "Todavía no hay un día con datos en RIA y SiAR a la vez."
            return empty

        def _fetch(d: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            siar_rows = _rows(
                conn,
                """
                SELECT provincia_nombre AS province_name,
                       COUNT(*)::int AS stations,
                       AVG(et0)::float AS et0_mm,
                       AVG(temp_media)::float AS mean_temp_c,
                       AVG(precipitacion)::float AS precip_mm,
                       AVG(humedad_media)::float AS mean_humidity_pct
                FROM raw.raw_siar_clima_diario
                WHERE ccaa_codigo='AND' AND fecha=CAST(:d AS date)
                  AND provincia_nombre IS NOT NULL
                GROUP BY provincia_nombre
                """,
                d=d,
            )
            ria_rows = _rows(
                conn,
                """
                SELECT provincia_nombre AS province_name,
                       COUNT(*)::int AS stations,
                       AVG(et0)::float AS et0_mm,
                       AVG(temp_media)::float AS mean_temp_c,
                       AVG(precipitacion)::float AS precip_mm,
                       AVG(humedad_media)::float AS mean_humidity_pct
                FROM raw.raw_ria_clima_diario
                WHERE fecha=CAST(:d AS date) AND provincia_nombre IS NOT NULL
                GROUP BY provincia_nombre
                """,
                d=d,
            )
            return siar_rows, ria_rows

        # Prefer caller's date only if both networks have provinces; else common.
        candidate = as_of or common
        siar, ria = _fetch(candidate)
        overlap = set(r["province_name"] for r in siar) & set(r["province_name"] for r in ria)
        if not overlap and candidate != common:
            candidate = common
            siar, ria = _fetch(candidate)
        as_of = candidate
        siar_by = {r["province_name"]: r for r in siar}
        ria_by = {r["province_name"]: r for r in ria}
        names = sorted(set(siar_by) & set(ria_by))
        by_province: list[dict[str, Any]] = []
        for name in names:
            s = siar_by[name]
            r = ria_by[name]
            by_province.append(
                {
                    "province_name": name,
                    "ria": {
                        "stations": r["stations"],
                        "et0_mm": _f(r["et0_mm"], 2),
                        "mean_temp_c": _f(r["mean_temp_c"], 1),
                        "precip_mm": _f(r["precip_mm"], 2),
                        "mean_humidity_pct": _f(r["mean_humidity_pct"], 0),
                    },
                    "siar": {
                        "stations": s["stations"],
                        "et0_mm": _f(s["et0_mm"], 2),
                        "mean_temp_c": _f(s["mean_temp_c"], 1),
                        "precip_mm": _f(s["precip_mm"], 2),
                        "mean_humidity_pct": _f(s["mean_humidity_pct"], 0),
                    },
                    "delta": {
                        "et0_mm": _f(
                            (s["et0_mm"] or 0) - (r["et0_mm"] or 0), 2
                        )
                        if s["et0_mm"] is not None and r["et0_mm"] is not None
                        else None,
                        "mean_temp_c": _f(
                            (s["mean_temp_c"] or 0) - (r["mean_temp_c"] or 0), 1
                        )
                        if s["mean_temp_c"] is not None and r["mean_temp_c"] is not None
                        else None,
                        "precip_mm": _f(
                            (s["precip_mm"] or 0) - (r["precip_mm"] or 0), 2
                        )
                        if s["precip_mm"] is not None and r["precip_mm"] is not None
                        else None,
                    },
                }
            )

        regional = None
        if by_province:
            def avg(path_a: str, path_b: str) -> float | None:
                vals = []
                for p in by_province:
                    v = p[path_a][path_b]
                    if v is not None:
                        vals.append(float(v))
                return sum(vals) / len(vals) if vals else None

            regional = {
                "province_name": "Andalucía",
                "ria": {
                    "stations": sum(p["ria"]["stations"] for p in by_province),
                    "et0_mm": _f(avg("ria", "et0_mm"), 2),
                    "mean_temp_c": _f(avg("ria", "mean_temp_c"), 1),
                    "precip_mm": _f(avg("ria", "precip_mm"), 2),
                    "mean_humidity_pct": _f(avg("ria", "mean_humidity_pct"), 0),
                },
                "siar": {
                    "stations": sum(p["siar"]["stations"] for p in by_province),
                    "et0_mm": _f(avg("siar", "et0_mm"), 2),
                    "mean_temp_c": _f(avg("siar", "mean_temp_c"), 1),
                    "precip_mm": _f(avg("siar", "precip_mm"), 2),
                    "mean_humidity_pct": _f(avg("siar", "mean_humidity_pct"), 0),
                },
                "delta": {
                    "et0_mm": _f(
                        (avg("siar", "et0_mm") or 0) - (avg("ria", "et0_mm") or 0), 2
                    ),
                    "mean_temp_c": _f(
                        (avg("siar", "mean_temp_c") or 0)
                        - (avg("ria", "mean_temp_c") or 0),
                        1,
                    ),
                    "precip_mm": _f(
                        (avg("siar", "precip_mm") or 0) - (avg("ria", "precip_mm") or 0),
                        2,
                    ),
                },
            }

        if not by_province:
            empty["as_of"] = as_of
            empty["note"] = (
                "No hay provincias con datos en RIA y SiAR el mismo día "
                f"({as_of}). Cuando coincidan, verás aquí la comparación."
            )
            return empty

        return {
            "available": True,
            "as_of": as_of,
            "note": (
                "Media provincial del mismo día. Δ = SiAR − RIA. "
                "Redes distintas (riego MAPA vs agroclimática IFAPA); las diferencias son esperables."
            ),
            "regional": regional,
            "by_province": by_province,
        }
    except Exception as exc:  # noqa: BLE001
        empty["note"] = "No se pudo comparar RIA y SiAR ahora mismo. Prueba más tarde."
        return empty


def build_heat_demand_cross(
    conn: Connection,
    *,
    as_of: str | None = None,
    lookback_days: int = 30,
) -> dict[str, Any]:
    """Cross heat-stress days with SiAR irrigation demand (same province/date).

    Peak days = heat stress (or SiAR Tmax>35 + low humidity) AND high SiAR demand.
    """
    from app.irrigation_autonomy import (
        DEFAULT_KC,
        IRRIGATED_HA_2023,
        KC_BY_PROVINCE,
        _daily_demand_hm3,
        _f,
    )

    empty = {
        "available": False,
        "as_of_heat": None,
        "as_of_siar": as_of,
        "lookback_days": lookback_days,
        "note": "Sin solape calor × demanda SiAR.",
        "definition_es": (
            "Cruza días de estrés térmico (Tmáx alta y aire seco) con la demanda de riego "
            "estimada con SiAR. Un pico es un día caluroso en el que el cultivo también pide mucha agua: "
            "ahí el embalse suele vaciarse más rápido."
        ),
        "regional": None,
        "by_province": [],
        "peak_days": [],
        "series": [],
    }
    try:
        heat_rows = _rows(
            conn,
            """
            SELECT
                observation_date::text AS d,
                province_name,
                stations_in_heat_stress::int AS stations_heat,
                ROUND(avg_max_temp_c::numeric, 1)::float AS tmax_c,
                ROUND(COALESCE(avg_min_humidity_pct, 0)::numeric, 1)::float AS min_rh_pct,
                ROUND(COALESCE(agricultural_risk_index, 0)::numeric, 2)::float AS agri_risk
            FROM marts.fact_heat_stress_days
            WHERE observation_date >= COALESCE(CAST(:d AS date), CURRENT_DATE) - (:n * INTERVAL '1 day')
              AND observation_date <= COALESCE(CAST(:d AS date), CURRENT_DATE)
            ORDER BY observation_date ASC, province_name
            """,
            d=as_of,
            n=lookback_days,
        )
        siar_rows = _rows(
            conn,
            """
            SELECT
                fecha::text AS d,
                provincia_nombre AS province_name,
                COUNT(*)::int AS station_count,
                AVG(et0)::float AS et0_mm,
                AVG(COALESCE(precip_efectiva, 0))::float AS pe_mm,
                AVG(COALESCE(precipitacion, 0))::float AS precip_mm,
                AVG(temp_max)::float AS tmax_c,
                AVG(COALESCE(humedad_min, humedad_media))::float AS min_rh_pct
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND'
              AND provincia_nombre IS NOT NULL
              AND et0 IS NOT NULL
              AND fecha >= COALESCE(CAST(:d AS date), CURRENT_DATE) - (:n * INTERVAL '1 day')
              AND fecha <= COALESCE(CAST(:d AS date), CURRENT_DATE)
            GROUP BY fecha, provincia_nombre
            ORDER BY fecha ASC, provincia_nombre
            """,
            d=as_of,
            n=lookback_days,
        )
    except Exception as exc:  # noqa: BLE001
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        empty["note"] = f"No se pudo cruzar calor y demanda: {exc}"
        return empty

    if not siar_rows:
        return empty

    heat_map: dict[tuple[str, str], dict[str, Any]] = {
        (r["d"], r["province_name"]): r for r in heat_rows
    }

    # Build joint daily rows
    joint: list[dict[str, Any]] = []
    for s in siar_rows:
        name = s["province_name"]
        d = s["d"]
        ha = int(IRRIGATED_HA_2023.get(name, 0))
        kc = float(KC_BY_PROVINCE.get(name, DEFAULT_KC))
        et0 = float(s.get("et0_mm") or 0)
        pe = float(s.get("pe_mm") or 0)
        demand = _daily_demand_hm3(et0, pe, ha, kc)
        h = heat_map.get((d, name))
        tmax_siar = s.get("tmax_c")
        rh_siar = s.get("min_rh_pct")
        # Heat from mart, or SiAR proxy (same spirit as fact_heat_stress_days)
        from_mart = h is not None and int(h.get("stations_heat") or 0) > 0
        tmax = float(h["tmax_c"]) if h and h.get("tmax_c") is not None else (
            float(tmax_siar) if tmax_siar is not None else None
        )
        rh = float(h["min_rh_pct"]) if h and h.get("min_rh_pct") is not None else (
            float(rh_siar) if rh_siar is not None else None
        )
        from_siar_proxy = (
            tmax is not None and rh is not None and tmax > 35 and rh < 30 and not from_mart
        )
        is_heat = bool(from_mart or from_siar_proxy)
        agri = float(h["agri_risk"]) if h and h.get("agri_risk") is not None else None
        # Peak pressure: demand × heat intensity (tmax above 35, or agri risk)
        heat_factor = 0.0
        if is_heat and tmax is not None:
            heat_factor = max(0.0, (tmax - 32.0) / 10.0)  # 35→0.3, 42→1.0
        elif is_heat:
            heat_factor = 0.5
        peak_index = demand * (1.0 + heat_factor) if is_heat else demand * 0.25

        joint.append(
            {
                "date": d,
                "province_name": name,
                "et0_mm": _f(et0, 2),
                "precip_mm": _f(float(s.get("precip_mm") or 0), 2),
                "daily_demand_hm3": _f(demand, 3),
                "tmax_c": _f(tmax, 1) if tmax is not None else None,
                "min_rh_pct": _f(rh, 1) if rh is not None else None,
                "stations_heat": int(h["stations_heat"]) if h else 0,
                "agri_risk": _f(agri, 2) if agri is not None else None,
                "is_heat_day": is_heat,
                "heat_source": "mart" if from_mart else ("siar_proxy" if from_siar_proxy else "none"),
                "peak_index": _f(peak_index, 3),
                "irrigated_ha": ha,
                "kc": _f(kc, 2),
            }
        )

    if not joint:
        return empty

    # Peak days: heat days in top tercile of demand among heat days, or top peak_index overall heat
    heat_joint = [j for j in joint if j["is_heat_day"]]
    peak_days: list[dict[str, Any]] = []
    if heat_joint:
        demands = sorted(float(j["daily_demand_hm3"] or 0) for j in heat_joint)
        cut = demands[max(0, int(len(demands) * 0.66))] if demands else 0.0
        candidates = [
            j for j in heat_joint if float(j["daily_demand_hm3"] or 0) >= cut
        ]
        candidates.sort(key=lambda x: float(x["peak_index"] or 0), reverse=True)
        peak_days = candidates[:12]

    # By province
    by_p: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for j in joint:
        by_p[j["province_name"]].append(j)

    by_province: list[dict[str, Any]] = []
    for name, rows in sorted(by_p.items()):
        heat_n = sum(1 for r in rows if r["is_heat_day"])
        dem_heat = [
            float(r["daily_demand_hm3"] or 0) for r in rows if r["is_heat_day"]
        ]
        dem_cool = [
            float(r["daily_demand_hm3"] or 0) for r in rows if not r["is_heat_day"]
        ]
        et0_heat = [float(r["et0_mm"] or 0) for r in rows if r["is_heat_day"]]
        et0_cool = [float(r["et0_mm"] or 0) for r in rows if not r["is_heat_day"]]
        last = rows[-1]
        peaks_p = [p for p in peak_days if p["province_name"] == name]
        avg = lambda xs: (sum(xs) / len(xs)) if xs else None
        by_province.append(
            {
                "province_name": name,
                "days_total": len(rows),
                "heat_days": heat_n,
                "peak_days_count": len(peaks_p),
                "avg_demand_heat_hm3": _f(avg(dem_heat), 3) if dem_heat else None,
                "avg_demand_other_hm3": _f(avg(dem_cool), 3) if dem_cool else None,
                "avg_et0_heat_mm": _f(avg(et0_heat), 2) if et0_heat else None,
                "avg_et0_other_mm": _f(avg(et0_cool), 2) if et0_cool else None,
                "demand_lift_pct": (
                    _f(
                        100.0
                        * ((avg(dem_heat) or 0) - (avg(dem_cool) or 0))
                        / (avg(dem_cool) or 1e-9),
                        0,
                    )
                    if dem_heat and dem_cool and avg(dem_cool)
                    else None
                ),
                "latest_date": last["date"],
                "latest_is_heat": last["is_heat_day"],
                "latest_demand_hm3": last["daily_demand_hm3"],
                "latest_tmax_c": last["tmax_c"],
                "latest_peak_index": last["peak_index"],
            }
        )

    by_province.sort(
        key=lambda x: (
            -(x["peak_days_count"] or 0),
            -(x["heat_days"] or 0),
            -(float(x["avg_demand_heat_hm3"] or 0)),
        )
    )

    # Regional daily series: mean tmax / sum demand / any heat
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for j in joint:
        by_date[j["date"]].append(j)
    series: list[dict[str, Any]] = []
    for d in sorted(by_date.keys()):
        rows = by_date[d]
        dem = sum(float(r["daily_demand_hm3"] or 0) for r in rows)
        tmx = [float(r["tmax_c"]) for r in rows if r.get("tmax_c") is not None]
        heat_n = sum(1 for r in rows if r["is_heat_day"])
        series.append(
            {
                "date": d,
                "daily_demand_hm3": _f(dem, 2),
                "avg_tmax_c": _f(sum(tmx) / len(tmx), 1) if tmx else None,
                "provinces_in_heat": heat_n,
                "peak_index": _f(
                    sum(float(r["peak_index"] or 0) for r in rows), 2
                ),
            }
        )

    heat_days_reg = sum(1 for s in series if int(s.get("provinces_in_heat") or 0) > 0)
    as_of_heat = max((r["d"] for r in heat_rows), default=None) if heat_rows else None
    as_of_siar = max((r["d"] for r in siar_rows), default=as_of)

    regional = {
        "province_name": "Andalucía",
        "days_total": len(series),
        "heat_days": heat_days_reg,
        "peak_days_count": len(peak_days),
        "avg_demand_heat_hm3": None,
        "avg_demand_other_hm3": None,
        "demand_lift_pct": None,
        "latest_date": series[-1]["date"] if series else None,
        "latest_is_heat": bool(series and int(series[-1].get("provinces_in_heat") or 0) > 0),
        "latest_demand_hm3": series[-1]["daily_demand_hm3"] if series else None,
        "latest_tmax_c": series[-1].get("avg_tmax_c") if series else None,
        "latest_peak_index": series[-1].get("peak_index") if series else None,
    }

    return {
        "available": True,
        "as_of_heat": as_of_heat,
        "as_of_siar": as_of_siar,
        "lookback_days": lookback_days,
        "note": "",
        "definition_es": empty["definition_es"],
        "regional": regional,
        "by_province": by_province,
        "peak_days": peak_days,
        "series": series,
    }

