"""SiAR station ↔ embalse / sistema de explotación map links (estimación).

Rule (documented as estimación — no official service-area polygons):
1. Primary: each Andalucía SiAR station is assigned to the nearest
   irrigation-relevant (non-urban) reservoir with known coordinates,
   if distance_km ≤ MAX_LINK_DISTANCE_KM.
2. Fallback: if no reservoir is close enough (or station coords missing
   for NN but province known), assign the province's dominant non-urban
   exploitation system by reservoir capacity (same proxy spirit as
   siar_by_system), without a specific embalse.

REDIAM catalog geometries are POINT in ETRS89/UTM zone 30N (EPSG:25830).
SiAR latitud_raw / longitud_raw are DMS or decimal strings from MAPA meta.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from sqlalchemy.engine import Connection

from app.irrigation_autonomy import URBAN_SQL_IN, URBAN_SUPPLY_SYSTEMS, _f, _rows

# Beyond this, prefer province-dominant system over a distant embalse.
MAX_LINK_DISTANCE_KM = 80.0

# ETRS89 / UTM zone 30N — REDIAM embalses catalog CRS.
UTM_ZONE = 30


def _empty() -> dict[str, Any]:
    return {
        "available": False,
        "as_of_siar": None,
        "method": "nearest_non_urban_reservoir_or_province_dominant_system",
        "method_es": (
            "Estimación: cada estación SiAR (Andalucía) se enlaza al embalse "
            "no urbano más cercano (≤ "
            f"{MAX_LINK_DISTANCE_KM:.0f} km) o, si no hay ninguno cerca, al "
            "sistema de explotación dominante de su provincia por capacidad. "
            "No hay polígonos oficiales de zona regable."
        ),
        "proxy_label_es": (
            "Estimación espacial (vecino más cercano / sistema dominante "
            "provincial). No es área de servicio oficial."
        ),
        "max_link_distance_km": MAX_LINK_DISTANCE_KM,
        "excluded_systems": sorted(URBAN_SUPPLY_SYSTEMS),
        "crs_reservoirs": "EPSG:25830→WGS84",
        "note_es": "",
        "caveats_es": [],
        "stations": [],
        "reservoirs": [],
        "by_system": [],
        "summary": {
            "station_count": 0,
            "linked_nearest": 0,
            "linked_province_fallback": 0,
            "unlinked": 0,
            "reservoir_count": 0,
            "system_count": 0,
        },
    }


def _caveats() -> list[str]:
    return [
        "No existen polígonos oficiales de zona regable estación∈sistema en este piloto.",
        "El enlace al embalse es por distancia geográfica (haversine), no por red de canales.",
        f"Si el embalse más cercano supera {MAX_LINK_DISTANCE_KM:.0f} km, se usa el sistema "
        "dominante de la provincia (cuota de capacidad no urbana).",
        "Se excluyen ABASTECIMIENTO DE SEVILLA y ABASTECIMIENTO DE JAÉN.",
        "Coordenadas de embalse: centroide/POINT del catálogo REDIAM (UTM 30N → WGS84).",
        "Coordenadas SiAR: latitud_raw/longitud_raw del catálogo MAPA (DMS o decimal).",
        "No sustituye balances de demarcación ni dotaciones oficiales.",
    ]


def parse_siar_coord(raw: Any, *, is_lon: bool = False) -> float | None:
    """Parse SiAR Latitud/Longitud (decimal, DMS, or packed DDMMSSmmm+hemi).

    MAPA often returns packed strings like ``365007000N`` / ``022408000W``
    (= 36°50′07.000″ N / 2°24′08.000″ W).
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    # Packed DDMMSSmmm + hemisphere (no separators) — common in SiAR catalog.
    packed = re.fullmatch(
        r"(\d{2,3})(\d{2})(\d{2})(\d{3})([NnSsEeOoWw])",
        s.replace(" ", ""),
    )
    if packed:
        deg = int(packed.group(1))
        minutes = int(packed.group(2))
        seconds = int(packed.group(3))
        millis = int(packed.group(4))
        hemi = packed.group(5).upper()
        val = deg + minutes / 60.0 + (seconds + millis / 1000.0) / 3600.0
        if hemi in ("S", "W", "O"):
            val = -val
        return val

    try:
        v = float(s.replace(",", "."))
        if abs(v) <= 180:
            # Bare positive longitude in Andalucía is west → negate if no hemisphere.
            if is_lon and v > 0 and not re.search(r"[EeWwOoNnSs]", str(raw)):
                # Heuristic: values 1–10 without letter are almost always west.
                if 0 < v < 15:
                    v = -v
            return v
    except ValueError:
        pass

    s2 = (
        s.replace("º", "°")
        .replace("ª", "°")
        .replace("''", '"')
        .replace("´", "'")
        .replace("′", "'")
        .replace("″", '"')
    )
    hemi = None
    m = re.search(r"([NnSsEeOoWw])\s*$", s2)
    if m:
        hemi = m.group(1).upper()
        s2 = s2[: m.start()].strip()
    nums = re.findall(r"[\d]+(?:[.,]\d+)?", s2)
    if not nums:
        return None
    deg = float(nums[0].replace(",", "."))
    minutes = float(nums[1].replace(",", ".")) if len(nums) > 1 else 0.0
    seconds = float(nums[2].replace(",", ".")) if len(nums) > 2 else 0.0
    val = deg + minutes / 60.0 + seconds / 3600.0
    if hemi in ("S", "W", "O"):
        val = -val
    elif hemi is None and is_lon and val > 0 and val < 15:
        val = -val
    return val


def utm_to_latlon(
    easting: float, northing: float, *, zone: int = UTM_ZONE, northern: bool = True
) -> tuple[float, float]:
    """WGS84 lat/lon from UTM (EPSG:25830 / UTM zone 30N for Andalucía)."""
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    k0 = 0.9996
    x = easting - 500000.0
    y = northing if northern else northing - 10_000_000.0
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    m_arc = y / k0
    mu = m_arc / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
    )
    n1 = a / math.sqrt(1 - e2 * math.sin(phi1) ** 2)
    t1 = math.tan(phi1) ** 2
    c1 = ep2 * math.cos(phi1) ** 2
    r1 = a * (1 - e2) / (1 - e2 * math.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * k0)
    lat = phi1 - (n1 * math.tan(phi1) / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2) * d**6 / 720
    )
    lon = lon0 + (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * d**5 / 120
    ) / math.cos(phi1)
    return math.degrees(lat), math.degrees(lon)


def parse_utm_point_wkt(wkt: str | None) -> tuple[float, float] | None:
    if not wkt:
        return None
    m = re.search(
        r"POINT\s*\(\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s*\)",
        str(wkt),
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _norm_prov(s: str | None) -> str:
    return (s or "").strip()


def _load_stations(conn: Connection) -> tuple[str | None, list[dict[str, Any]]]:
    latest = _rows(
        conn,
        """
        SELECT MAX(fecha)::text AS d
        FROM raw.raw_siar_clima_diario
        WHERE ccaa_codigo = 'AND'
        """,
    )
    as_of = (latest[0].get("d") if latest else None) or None
    rows: list[dict[str, Any]] = []
    try:
        rows = _rows(
            conn,
            """
            SELECT
                TRIM(codigo_estacion) AS station_code,
                NULLIF(TRIM(nombre_estacion), '') AS station_name,
                NULLIF(TRIM(provincia_nombre), '') AS province_name,
                latitud_raw,
                longitud_raw
            FROM raw.raw_siar_estaciones
            WHERE ccaa_codigo = 'AND'
              AND TRIM(COALESCE(codigo_estacion, '')) <> ''
            """,
        )
    except Exception:
        rows = []
    if not rows:
        rows = _rows(
            conn,
            """
            SELECT DISTINCT ON (codigo_estacion)
                TRIM(codigo_estacion) AS station_code,
                NULLIF(TRIM(nombre_estacion), '') AS station_name,
                NULLIF(TRIM(provincia_nombre), '') AS province_name,
                latitud_raw,
                longitud_raw
            FROM raw.raw_siar_clima_diario
            WHERE ccaa_codigo = 'AND'
              AND TRIM(COALESCE(codigo_estacion, '')) <> ''
            ORDER BY
                codigo_estacion,
                (NULLIF(TRIM(latitud_raw), '') IS NULL),
                (NULLIF(TRIM(longitud_raw), '') IS NULL),
                fecha DESC NULLS LAST
            """,
        )
    stations: list[dict[str, Any]] = []
    for r in rows:
        lat = parse_siar_coord(r.get("latitud_raw"), is_lon=False)
        lon = parse_siar_coord(r.get("longitud_raw"), is_lon=True)
        # Andalucía bbox sanity
        if lat is not None and not (35.5 <= lat <= 39.5):
            lat = None
        if lon is not None and not (-8.0 <= lon <= -0.5):
            lon = None
        stations.append(
            {
                "station_code": str(r["station_code"]),
                "station_name": r.get("station_name") or str(r["station_code"]),
                "province_name": _norm_prov(r.get("province_name")),
                "lat": _f(lat, 5) if lat is not None else None,
                "lon": _f(lon, 5) if lon is not None else None,
            }
        )
    return as_of, stations


def _load_reservoirs(conn: Connection) -> list[dict[str, Any]]:
    rows = _rows(
        conn,
        f"""
        SELECT
            TRIM(r.reservoir_code) AS reservoir_code,
            COALESCE(NULLIF(TRIM(r.reservoir_name), ''), TRIM(r.reservoir_code))
                AS reservoir_name,
            NULLIF(TRIM(r.province_name), '') AS province_name,
            COALESCE(NULLIF(TRIM(r.exploitation_system), ''), 'Sin sistema')
                AS exploitation_system,
            COALESCE(NULLIF(TRIM(r.watershed_demarcation), ''), '—')
                AS watershed_demarcation,
            r.geometry_wkt,
            r.reservoir_capacity_hm3::float AS capacity_hm3
        FROM marts.dim_reservoirs r
        WHERE r.geometry_wkt IS NOT NULL
          AND TRIM(r.geometry_wkt) <> ''
          AND UPPER(TRIM(COALESCE(r.exploitation_system, '')))
              NOT IN ({URBAN_SQL_IN})
          AND TRIM(COALESCE(r.exploitation_system, '')) <> ''
        """,
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        xy = parse_utm_point_wkt(r.get("geometry_wkt"))
        if not xy:
            continue
        lat, lon = utm_to_latlon(xy[0], xy[1], zone=UTM_ZONE)
        if not (35.5 <= lat <= 39.5 and -8.0 <= lon <= -0.5):
            continue
        out.append(
            {
                "reservoir_code": str(r["reservoir_code"]),
                "reservoir_name": str(r["reservoir_name"]),
                "province_name": _norm_prov(r.get("province_name")),
                "exploitation_system": str(r["exploitation_system"]),
                "watershed_demarcation": str(r["watershed_demarcation"]),
                "lat": _f(lat, 5),
                "lon": _f(lon, 5),
                "capacity_hm3": _f(r.get("capacity_hm3"), 2),
            }
        )
    return out


def _dominant_system_by_province(
    reservoirs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Province → dominant non-urban system by capacity (largest embalse sum)."""
    acc: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    meta: dict[str, dict[str, str]] = {}
    for r in reservoirs:
        prov = r.get("province_name") or ""
        sys_name = r.get("exploitation_system") or ""
        if not prov or not sys_name:
            continue
        cap = float(r.get("capacity_hm3") or 0.0)
        acc[prov][sys_name] += max(cap, 0.0)
        meta.setdefault(sys_name, {}).setdefault(
            "watershed_demarcation", r.get("watershed_demarcation") or "—"
        )
    dominant: dict[str, dict[str, Any]] = {}
    for prov, systems in acc.items():
        best_sys, best_cap = max(systems.items(), key=lambda kv: kv[1])
        dominant[prov] = {
            "exploitation_system": best_sys,
            "capacity_hm3": _f(best_cap, 2),
            "watershed_demarcation": meta.get(best_sys, {}).get(
                "watershed_demarcation", "—"
            ),
        }
    return dominant


def link_stations(
    stations: list[dict[str, Any]],
    reservoirs: list[dict[str, Any]],
    *,
    max_km: float = MAX_LINK_DISTANCE_KM,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Pure linking (testable). Returns (station rows, counts)."""
    dominant = _dominant_system_by_province(reservoirs)
    linked: list[dict[str, Any]] = []
    counts = {"nearest": 0, "province_fallback": 0, "unlinked": 0}

    for st in stations:
        base = {
            "station_code": st["station_code"],
            "station_name": st.get("station_name") or st["station_code"],
            "province_name": st.get("province_name") or "",
            "lat": st.get("lat"),
            "lon": st.get("lon"),
            "is_estimate": True,
            "link_method": None,
            "reservoir_code": None,
            "reservoir_name": None,
            "exploitation_system": None,
            "watershed_demarcation": None,
            "distance_km": None,
        }
        lat, lon = st.get("lat"), st.get("lon")
        best = None
        best_d = None
        if lat is not None and lon is not None and reservoirs:
            for r in reservoirs:
                if r.get("lat") is None or r.get("lon") is None:
                    continue
                d = haversine_km(float(lat), float(lon), float(r["lat"]), float(r["lon"]))
                if best_d is None or d < best_d:
                    best_d = d
                    best = r
        if best is not None and best_d is not None and best_d <= max_km:
            base.update(
                {
                    "link_method": "nearest_reservoir",
                    "reservoir_code": best["reservoir_code"],
                    "reservoir_name": best["reservoir_name"],
                    "exploitation_system": best["exploitation_system"],
                    "watershed_demarcation": best.get("watershed_demarcation"),
                    "distance_km": _f(best_d, 2),
                }
            )
            counts["nearest"] += 1
        else:
            prov = st.get("province_name") or ""
            dom = dominant.get(prov)
            if dom:
                base.update(
                    {
                        "link_method": "province_dominant_system",
                        "reservoir_code": None,
                        "reservoir_name": None,
                        "exploitation_system": dom["exploitation_system"],
                        "watershed_demarcation": dom.get("watershed_demarcation"),
                        "distance_km": _f(best_d, 2) if best_d is not None else None,
                    }
                )
                counts["province_fallback"] += 1
            else:
                counts["unlinked"] += 1
        linked.append(base)
    return linked, counts


def build_station_reservoir_links(conn: Connection) -> dict[str, Any]:
    out = _empty()
    out["caveats_es"] = _caveats()
    try:
        as_of, stations = _load_stations(conn)
        out["as_of_siar"] = as_of
        reservoirs = _load_reservoirs(conn)
        if not stations:
            out["note_es"] = "Sin estaciones SiAR (Andalucía) en raw.raw_siar_clima_diario."
            return out
        if not reservoirs:
            out["note_es"] = (
                "Sin embalses no urbanos con geometría en marts.dim_reservoirs."
            )
            # still try province fallback won't work without reservoirs
            linked, counts = link_stations(stations, [])
            out["stations"] = linked
            out["summary"] = {
                "station_count": len(linked),
                "linked_nearest": counts["nearest"],
                "linked_province_fallback": counts["province_fallback"],
                "unlinked": counts["unlinked"],
                "reservoir_count": 0,
                "system_count": 0,
            }
            out["available"] = False
            return out

        linked, counts = link_stations(stations, reservoirs)
        # Enrich reservoirs with linked station counts
        link_n: dict[str, int] = defaultdict(int)
        sys_stations: dict[str, set[str]] = defaultdict(set)
        sys_reservoirs: dict[str, set[str]] = defaultdict(set)
        for s in linked:
            sys_name = s.get("exploitation_system")
            if sys_name:
                sys_stations[sys_name].add(s["station_code"])
            rc = s.get("reservoir_code")
            if rc:
                link_n[rc] += 1
        for r in reservoirs:
            sys_reservoirs[r["exploitation_system"]].add(r["reservoir_code"])
            r["linked_station_count"] = int(link_n.get(r["reservoir_code"], 0))

        by_system = []
        for sys_name in sorted(set(sys_stations) | set(sys_reservoirs)):
            by_system.append(
                {
                    "exploitation_system": sys_name,
                    "station_count": len(sys_stations.get(sys_name, ())),
                    "reservoir_count": len(sys_reservoirs.get(sys_name, ())),
                    "is_estimate": True,
                }
            )
        by_system.sort(key=lambda x: (-x["station_count"], x["exploitation_system"]))

        out["stations"] = sorted(
            linked, key=lambda s: (s.get("province_name") or "", s["station_code"])
        )
        out["reservoirs"] = sorted(
            reservoirs, key=lambda r: (r.get("province_name") or "", r["reservoir_name"])
        )
        out["by_system"] = by_system
        out["summary"] = {
            "station_count": len(linked),
            "linked_nearest": counts["nearest"],
            "linked_province_fallback": counts["province_fallback"],
            "unlinked": counts["unlinked"],
            "reservoir_count": len(reservoirs),
            "system_count": len(by_system),
        }
        out["available"] = bool(counts["nearest"] or counts["province_fallback"])
        if out["available"]:
            out["note_es"] = (
                f"{counts['nearest']} estaciones → embalse más cercano; "
                f"{counts['province_fallback']} → sistema dominante provincial; "
                f"{counts['unlinked']} sin enlace."
            )
        else:
            out["note_es"] = "No se pudo enlazar ninguna estación."
        return out
    except Exception as exc:  # noqa: BLE001
        out["note_es"] = f"Error enlazando estaciones SiAR × embalses: {exc}"
        return out
