"""Extras for irrigation tab: 7d autonomy projection + RIA vs SiAR compare."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.irrigation_autonomy import (
    DEFAULT_KC,
    IRRIGATED_HA_2023,
    KC_BY_PROVINCE,
    _daily_demand_hm3,
    _f,
    _risk_level,
)
from app.provinces_meta import PROVINCES
from app.meteo_forecast import OM_LAT as _OM_LAT, OM_LON as _OM_LON

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 30 * 60


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
        projected.append(
            {
                "province_name": name,
                "available": True,
                "kc": _f(kc, 2),
                "irrigated_ha": ha,
                "stored_start_hm3": base.get("stored_hm3"),
                "stored_end_hm3": series[-1]["stored_hm3"] if series else None,
                "cumulative_demand_hm3": _f(cum_demand, 3),
                "days_autonomy_start": base.get("days_autonomy"),
                "days_autonomy_end": end_days,
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
        regional = {
            "province_name": "Andalucía",
            "available": True,
            "stored_start_hm3": _f(stored0, 1),
            "stored_end_hm3": series_r[-1]["stored_hm3"] if series_r else None,
            "cumulative_demand_hm3": _f(cum, 3),
            "days_autonomy_start": None,
            "days_autonomy_end": end_days,
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


def build_ria_siar_compare(conn: Connection, as_of: str | None = None) -> dict[str, Any]:
    """Side-by-side RIA vs SiAR provincial means for the latest common date."""
    empty = {
        "available": False,
        "as_of": None,
        "note": "",
        "regional": None,
        "by_province": [],
    }
    try:
        if not as_of:
            rows = _rows(
                conn,
                """
                SELECT LEAST(
                    (SELECT MAX(fecha) FROM raw.raw_siar_clima_diario WHERE ccaa_codigo='AND'),
                    (SELECT MAX(fecha) FROM raw.raw_ria_clima_diario)
                )::text AS d
                """,
            )
            as_of = rows[0]["d"] if rows else None
        if not as_of:
            empty["note"] = "Sin fechas comunes RIA/SiAR."
            return empty

        siar = _rows(
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
            d=as_of,
        )
        ria = _rows(
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
            d=as_of,
        )
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

        return {
            "available": bool(by_province),
            "as_of": as_of,
            "note": (
                "Media provincial del mismo día. Δ = SiAR − RIA. "
                "Redes distintas (riego MAPA vs agroclimática IFAPA); las diferencias son esperables."
            ),
            "regional": regional,
            "by_province": by_province,
        }
    except Exception as exc:  # noqa: BLE001
        empty["note"] = f"Error comparando RIA/SiAR: {exc}"
        return empty
