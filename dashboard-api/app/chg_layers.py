"""Public CHG (Confederación Hidrográfica del Guadalquivir) geospatial layers.

Sources (open IDE-CHG GeoServer — no private CR portals):
  WFS: https://idechg.chguadalquivir.es/geoserver/ggiscloud_root/ows
  WMS: https://idechg.chguadalquivir.es/geoserver/ggiscloud_root/wms

Native CRS is typically EPSG:25830; we request EPSG:4326 for Leaflet/GeoJSON.
WFS 2.0 GetFeature currently returns HTTP 401 on this server; use WFS 1.1.0.

recintos_riego_pub has ~350k polygons — served as WMS tiles for the map;
sistemas / balsas / patrimonio / dotación olivar / zonas sobreexplotadas y vulnerables / PES sequía+escasez / piezómetros ship as simplified GeoJSON with disk cache.
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHG_WFS_BASE = "https://idechg.chguadalquivir.es/geoserver/ggiscloud_root/ows"
CHG_WMS_BASE = "https://idechg.chguadalquivir.es/geoserver/ggiscloud_root/wms"
CHG_WORKSPACE = "ggiscloud_root"
USER_AGENT = "andalucia-drought-monitor/1.0 (+https://andalucia.luisandresvelazquez.com)"
DEFAULT_SRS = "EPSG:4326"
WFS_VERSION = "1.1.0"

# Layers update roughly monthly; cache aggressively so we don't hammer GeoServer.
DEFAULT_CACHE_TTL_S = int(os.environ.get("CHG_CACHE_TTL_S", str(24 * 3600)))
DEFAULT_CACHE_DIR = os.environ.get(
    "CHG_CACHE_DIR",
    os.path.join(os.environ.get("TMPDIR", "/tmp"), "andalucia-chg-cache"),
)
HTTP_TIMEOUT_S = float(os.environ.get("CHG_HTTP_TIMEOUT_S", "90"))
HTTP_RETRIES = int(os.environ.get("CHG_HTTP_RETRIES", "3"))

# Overview simplify (~0.005° ≈ 500 m). Enough for dashboard map, not cadastral.
DEFAULT_SIMPLIFY_TOL_DEG = float(os.environ.get("CHG_SIMPLIFY_TOL_DEG", "0.005"))
# PES polygons are multi-MB raw; simplify more aggressively for map (~1–1.5 km).
PES_SIMPLIFY_TOL_DEG = float(os.environ.get("CHG_PES_SIMPLIFY_TOL_DEG", "0.01"))

# Official PES escenario / estado labels (Plan Especial de Sequías CHG).
PES_ESCASEZ_ORDER = ("Normalidad", "Prealerta", "Alerta", "Emergencia")
PES_SEQUIA_ORDER = ("Ausencia", "Sequía prolongada")

# Name tokens that hint Huelva–Sevilla / Doñana context (UTE / zona names).
DONANA_HUELVA_SEVILLA_TOKENS = (
    "doñana", "donana", "marismas", "guadiamar", "huelva", "almonte",
    "condado", "rocina", "cabezudos", "abalsadero", "sevilla",
)

PIEZOMETROS_WATER_NETWORKS_URL = (
    "https://idechg.chguadalquivir.es/geoportal/"
)

ATTRIBUTION_ES = (
    "© Confederación Hidrográfica del Guadalquivir (CHG) — IDE-CHG / datos.gob.es"
)
ATTRIBUTION_HTML = (
    '&copy; <a href="https://www.chguadalquivir.es/" target="_blank" rel="noopener">'
    "CHG</a> IDE-CHG"
)

# In-process memo of last successful payload per layer id.
_mem_cache: dict[str, dict[str, Any]] = {}


def _layer_catalog() -> list[dict[str, Any]]:
    """Static catalog (no network). feature_count_hint from live probes 2026-09."""
    return [
        {
            "id": "sistemas_explotacion",
            "type_name": f"{CHG_WORKSPACE}:sistemas_explotacion",
            "title_es": "Sistemas de explotación",
            "title_en": "Exploitation systems",
            "render": "geojson",
            "endpoint": "/api/gis/chg/sistemas_explotacion.geojson",
            "feature_count_hint": 10,
            "simplify": True,
            "max_features": None,
            "enabled_default": True,
            "priority": 1,
            "note_es": (
                "Polígonos oficiales CHG de sistemas de explotación. "
                "Geometrías simplificadas para el mapa web."
            ),
        },
        {
            "id": "recintos_riego_pub",
            "type_name": f"{CHG_WORKSPACE}:recintos_riego_pub",
            "title_es": "Recintos de riego autorizados",
            "title_en": "Authorized irrigation parcels",
            "render": "wms",
            "endpoint": "/api/gis/chg/recintos_riego_pub.geojson",
            "wms_url": CHG_WMS_BASE,
            "wms_layers": f"{CHG_WORKSPACE}:recintos_riego_pub",
            "feature_count_hint": 348975,
            "simplify": False,
            "max_features": None,
            "enabled_default": False,
            "priority": 1,
            "note_es": (
                "Superficies autorizadas para el riego (datos.gob.es / IDE-CHG). "
                "≈349 000 polígonos: en el mapa se usan teselas WMS; "
                "el endpoint GeoJSON solo admite muestras acotadas (maxFeatures)."
            ),
            "datos_gob_es": (
                "https://datos.gob.es/es/catalogo/"
                "ea0043519-superficies-autorizadas-para-el-riego-en-la-"
                "demarcacion-hidrografica-del-guadalquivir"
            ),
        },
        {
            "id": "balsas",
            "type_name": f"{CHG_WORKSPACE}:balsas",
            "title_es": "Balsas",
            "title_en": "Irrigation ponds",
            "render": "geojson",
            "endpoint": "/api/gis/chg/balsas.geojson",
            "feature_count_hint": 189,
            "simplify": True,
            "max_features": None,
            "enabled_default": False,
            "priority": 2,
            "note_es": "Balsas de riego CHG (capa ligera).",
        },
        {
            "id": "patrimonio_zonas_regables",
            "type_name": f"{CHG_WORKSPACE}:patrimonio_zonas_regables",
            "title_es": "Zonas regables (patrimonio)",
            "title_en": "Irrigable zones (heritage)",
            "render": "geojson",
            "endpoint": "/api/gis/chg/patrimonio_zonas_regables.geojson",
            "feature_count_hint": 9,
            "simplify": True,
            "max_features": None,
            "enabled_default": False,
            "priority": 2,
            "note_es": "Zonas regables del patrimonio hidráulico CHG (simplificadas).",
        },
        {
            "id": "canales",
            "type_name": f"{CHG_WORKSPACE}:canales",
            "title_es": "Canales",
            "title_en": "Canals",
            "render": "geojson",
            "endpoint": "/api/gis/chg/canales.geojson",
            "feature_count_hint": 1345,
            "simplify": True,
            "max_features": 2000,
            "enabled_default": False,
            "priority": 3,
            "note_es": (
                "Trazados de canales. Puede ser pesado; se simplifica y se "
                "limita el número de tramos."
            ),
        },
        {
            "id": "dotacion_olivar",
            "type_name": f"{CHG_WORKSPACE}:dotacion_olivar",
            "title_es": "Dotación olivar",
            "title_en": "Olive allotment",
            "render": "geojson",
            "endpoint": "/api/gis/chg/dotacion_olivar.geojson",
            "feature_count_hint": 50,
            "simplify": True,
            "max_features": None,
            "enabled_default": True,
            "priority": 1,
            "note_es": (
                "Dotaciones de riego de olivar (CHG): precipitación, ETP y "
                "volúmenes de referencia para tradicional / intensivo / "
                "superintensivo. Contexto de asignación; no sustituye la "
                "dotación oficial vigente."
            ),
        },
        {
            "id": "zonas_sobreexplotadas",
            "type_name": f"{CHG_WORKSPACE}:zonas_sobreexplotadas",
            "title_es": "Zonas sobreexplotadas",
            "title_en": "Overexploited zones",
            "render": "geojson",
            "endpoint": "/api/gis/chg/zonas_sobreexplotadas.geojson",
            "feature_count_hint": 7,
            "simplify": True,
            "max_features": None,
            "enabled_default": False,
            "priority": 2,
            "note_es": (
                "Masas / zonas declaradas sobreexplotadas en el ámbito CHG "
                "(pocos polígonos; geometrías simplificadas). Útil junto al "
                "plan Doñana para contexto de presión hídrica en Huelva–Sevilla, "
                "sin confundir con la zonificación REDIAM."
            ),
        },
        {
            "id": "zonas_vulnerables",
            "type_name": f"{CHG_WORKSPACE}:zonas_vulnerables",
            "title_es": "Zonas vulnerables (nitratos)",
            "title_en": "Vulnerable zones (nitrates)",
            "render": "geojson",
            "endpoint": "/api/gis/chg/zonas_vulnerables.geojson",
            "feature_count_hint": 15,
            "simplify": True,
            "max_features": None,
            "enabled_default": False,
            "priority": 2,
            "note_es": (
                "Zonas vulnerables a la contaminación por nitratos (CHG). "
                "Geometrías densas: se simplifican para el mapa web."
            ),
        },
        {
            "id": "pes_estado_sequia",
            "type_name": f"{CHG_WORKSPACE}:pes_estado_sequia",
            "title_es": "Estado sequía PES",
            "title_en": "PES drought status",
            "render": "geojson",
            "endpoint": "/api/gis/chg/pes_estado_sequia.geojson",
            "feature_count_hint": 27,
            "simplify": True,
            "simplify_tol_deg": PES_SIMPLIFY_TOL_DEG,
            "max_features": None,
            "enabled_default": True,
            "priority": 1,
            "group": "pes",
            "style_mode": "estado_sequia",
            "note_es": (
                "Estado de sequía prolongada del Plan Especial de Sequías (PES) CHG "
                "por zona (~27). Escenarios oficiales; no es el índice ICRA ni REDIAM. "
                "Prioridad contextual Huelva–Sevilla / Doñana (p. ej. Madre de las Marismas, "
                "Guadiamar, Rivera de Huelva). Geometrías muy simplificadas."
            ),
            "datos_gob_es": (
                "https://datos.gob.es/es/catalogo"
            ),
        },
        {
            "id": "pes_estado_escasez",
            "type_name": f"{CHG_WORKSPACE}:pes_estado_escasez",
            "title_es": "Escasez PES",
            "title_en": "PES scarcity status",
            "render": "geojson",
            "endpoint": "/api/gis/chg/pes_estado_escasez.geojson",
            "feature_count_hint": 25,
            "simplify": True,
            "simplify_tol_deg": PES_SIMPLIFY_TOL_DEG,
            "max_features": None,
            "enabled_default": True,
            "priority": 1,
            "group": "pes",
            "style_mode": "escenario_escasez",
            "note_es": (
                "Escenarios de escasez del Plan Especial de Sequías (PES) CHG por UTE "
                "(~25): Normalidad / Prealerta / Alerta / Emergencia. Accionable para "
                "posibles restricciones de riego. Destaca UTEs del entorno Doñana / "
                "Huelva–Sevilla (Madre de las Marismas, Guadiamar, Rivera de Huelva). "
                "No es ICRA. Geometrías densas: se simplifican agresivamente (~0,01°)."
            ),
            "datos_gob_es": (
                "https://datos.gob.es/es/catalogo"
            ),
        },
        {
            "id": "piezometros",
            "type_name": f"{CHG_WORKSPACE}:piezometros",
            "title_es": "Piezómetros",
            "title_en": "Piezometers",
            "render": "geojson",
            "endpoint": "/api/gis/chg/piezometros.geojson",
            "feature_count_hint": 334,
            "simplify": False,
            "max_features": None,
            "enabled_default": True,
            "priority": 1,
            "group": "groundwater",
            "style_mode": "point",
            "highlight_provinces": ["Huelva", "Sevilla"],
            "note_es": (
                "Red de piezómetros CHG (~334 puntos): nivel freático / masas "
                "subterráneas. Útil junto a Doñana y zonas sobreexplotadas en "
                "Huelva–Sevilla. Series históricas: consultar el visor de redes "
                "hídrica de la IDE-CHG (no se scrapean aquí)."
            ),
            "series_note_es": (
                "Series históricas en el visor IDE-CHG (water-networks / geoportal); "
                "este monitor solo muestra la ubicación y metadatos del punto."
            ),
            "series_url": PIEZOMETROS_WATER_NETWORKS_URL,
        },
        {
            "id": "explotacion_saih",
            "type_name": f"{CHG_WORKSPACE}:explotacion_saih",
            "title_es": "Explotación SAIH",
            "title_en": "SAIH exploitation points",
            "render": "geojson",
            "endpoint": "/api/gis/chg/explotacion_saih.geojson",
            "feature_count_hint": 427,
            "simplify": False,
            "max_features": None,
            "enabled_default": False,
            "priority": 3,
            "group": "saih",
            "note_es": (
                "Puntos de explotación SAIH (~427). Catálogo opcional; OFF por defecto."
            ),
        },
        {
            "id": "aforos",
            "type_name": f"{CHG_WORKSPACE}:aforos",
            "title_es": "Aforos",
            "title_en": "Gauging stations",
            "render": "geojson",
            "endpoint": "/api/gis/chg/aforos.geojson",
            "feature_count_hint": 68,
            "simplify": False,
            "max_features": None,
            "enabled_default": False,
            "priority": 3,
            "group": "saih",
            "note_es": (
                "Estaciones de aforo CHG (~68). Catálogo opcional; OFF por defecto."
            ),
        },
    ]


LAYER_BY_ID: dict[str, dict[str, Any]] = {L["id"]: L for L in _layer_catalog()}


def normalize_escenario_escasez(raw: str | None) -> str:
    """Map free-text escenario to canonical PES bucket (unit-tested)."""
    s = (raw or "").strip()
    if not s:
        return "Desconocido"
    low = s.casefold()
    if "emerg" in low:
        return "Emergencia"
    if "alerta" in low and "pre" not in low:
        return "Alerta"
    if "prealerta" in low or "pre-alerta" in low or "pre alerta" in low:
        return "Prealerta"
    if "normal" in low:
        return "Normalidad"
    # Exact title-case match if already canonical
    for canon in PES_ESCASEZ_ORDER:
        if low == canon.casefold():
            return canon
    return s


def normalize_estado_sequia(raw: str | None) -> str:
    """Map free-text estado sequía to canonical bucket (unit-tested)."""
    s = (raw or "").strip()
    if not s:
        return "Desconocido"
    low = s.casefold()
    if "prolong" in low or "sequ" in low:
        return "Sequía prolongada"
    if "ausen" in low or "normal" in low or "sin sequ" in low:
        return "Ausencia"
    for canon in PES_SEQUIA_ORDER:
        if low == canon.casefold():
            return canon
    return s


def worst_escenario(buckets: dict[str, int] | None) -> str | None:
    """Return worst PES escasez escenario present (Emergencia > … > Normalidad)."""
    if not buckets:
        return None
    present = [k for k, n in buckets.items() if n and k in PES_ESCASEZ_ORDER]
    if not present:
        # any non-zero unknown
        for k, n in buckets.items():
            if n:
                return k
        return None
    return max(present, key=lambda k: PES_ESCASEZ_ORDER.index(k))


def worst_estado_sequia(buckets: dict[str, int] | None) -> str | None:
    if not buckets:
        return None
    present = [k for k, n in buckets.items() if n and k in PES_SEQUIA_ORDER]
    if not present:
        for k, n in buckets.items():
            if n:
                return k
        return None
    return max(present, key=lambda k: PES_SEQUIA_ORDER.index(k))


def matches_donana_huelva_sevilla(name: str | None) -> bool:
    """True if UTE/zona name suggests Doñana / Huelva–Sevilla context."""
    low = (name or "").casefold()
    if not low:
        return False
    # normalize accents for matching
    trans = str.maketrans("áéíóúüñ", "aeiouun")
    low_ascii = low.translate(trans)
    for tok in DONANA_HUELVA_SEVILLA_TOKENS:
        t = tok.translate(trans) if hasattr(tok, "translate") else tok
        if t in low_ascii or tok in low:
            return True
    return False


def bucket_counts(values: list[str], order: tuple[str, ...]) -> dict[str, int]:
    """Count values; keep canonical order first, then extras."""
    counts: dict[str, int] = {k: 0 for k in order}
    for v in values:
        if v in counts:
            counts[v] += 1
        else:
            counts[v] = counts.get(v, 0) + 1
    return counts


def summarize_pes_features(
    features: list[dict[str, Any]],
    *,
    kind: str,
) -> dict[str, Any]:
    """Build KPI summary from property-only (or full) GeoJSON features.

    kind: "escasez" | "sequia"
    """
    rows: list[dict[str, Any]] = []
    labels: list[str] = []
    dates: list[str] = []
    highlight: list[dict[str, Any]] = []

    for feat in features:
        props = feat.get("properties") if isinstance(feat, dict) else None
        if not isinstance(props, dict):
            continue
        if kind == "escasez":
            name = props.get("nom_ute") or props.get("cod_ute") or ""
            bucket = normalize_escenario_escasez(props.get("escenario"))
            idx = props.get("indicador")
            code = props.get("cod_ute")
            fecha = props.get("fecha")
            row = {
                "cod_ute": code,
                "nom_ute": props.get("nom_ute"),
                "escenario": bucket,
                "escenario_raw": props.get("escenario"),
                "indicador": idx,
                "fecha": fecha,
                "highlight_donana_huelva_sevilla": matches_donana_huelva_sevilla(str(name)),
            }
        else:
            name = props.get("nom_szona") or props.get("cod_szona") or ""
            bucket = normalize_estado_sequia(props.get("estado"))
            idx = props.get("indice")
            code = props.get("cod_szona")
            fecha = props.get("fecha")
            row = {
                "cod_szona": code,
                "nom_szona": props.get("nom_szona"),
                "estado": bucket,
                "estado_raw": props.get("estado"),
                "indice": idx,
                "fecha": fecha,
                "highlight_donana_huelva_sevilla": matches_donana_huelva_sevilla(str(name)),
            }
        rows.append(row)
        labels.append(bucket)
        if fecha:
            dates.append(str(fecha).rstrip("Z"))
        if row["highlight_donana_huelva_sevilla"]:
            highlight.append(row)

    order = PES_ESCASEZ_ORDER if kind == "escasez" else PES_SEQUIA_ORDER
    counts = bucket_counts(labels, order)
    as_of = max(dates) if dates else None
    if kind == "escasez":
        worst = worst_escenario(counts)
        worst_label_es = {
            "Normalidad": "Normalidad",
            "Prealerta": "Prealerta",
            "Alerta": "Alerta",
            "Emergencia": "Emergencia",
        }.get(worst or "", worst)
        headline = (
            f"Escasez PES: {counts.get('Emergencia', 0)} emergencia, "
            f"{counts.get('Alerta', 0)} alerta, {counts.get('Prealerta', 0)} prealerta, "
            f"{counts.get('Normalidad', 0)} normalidad"
            + (f" · peor: {worst_label_es}" if worst else "")
        )
        return {
            "kind": "escasez",
            "available": bool(rows),
            "feature_count": len(rows),
            "as_of": as_of,
            "counts_by_escenario": counts,
            "worst_escenario": worst,
            "worst_label_es": worst_label_es,
            "highlight_donana_huelva_sevilla": highlight,
            "highlight_count": len(highlight),
            "headline_es": headline,
            "units_label_es": "UTE",
            "caveat_es": (
                "Escenarios del Plan Especial de Sequías (CHG). No es ICRA."
            ),
        }

    worst = worst_estado_sequia(counts)
    headline = (
        f"Sequía PES: {counts.get('Sequía prolongada', 0)} prolongada, "
        f"{counts.get('Ausencia', 0)} ausencia"
        + (f" · peor: {worst}" if worst else "")
    )
    return {
        "kind": "sequia",
        "available": bool(rows),
        "feature_count": len(rows),
        "as_of": as_of,
        "counts_by_estado": counts,
        "worst_estado": worst,
        "worst_label_es": worst,
        "highlight_donana_huelva_sevilla": highlight,
        "highlight_count": len(highlight),
        "headline_es": headline,
        "units_label_es": "zona",
        "caveat_es": (
            "Estado de sequía prolongada del PES (CHG). No es ICRA ni REDIAM."
        ),
    }


def _pes_summary_cache_paths(cache_dir: str) -> tuple[Path, Path]:
    return (
        Path(cache_dir) / "pes_kpi_summary.json",
        Path(cache_dir) / "pes_kpi_summary.meta.json",
    )


def fetch_pes_kpi_summary(
    *,
    force_refresh: bool = False,
    cache_dir: str | None = None,
    cache_ttl_s: int | None = None,
) -> dict[str, Any]:
    """Lightweight PES KPI (properties only, no geometries) with 24h disk+memory cache."""
    cdir = cache_dir or DEFAULT_CACHE_DIR
    ttl = DEFAULT_CACHE_TTL_S if cache_ttl_s is None else cache_ttl_s
    mem_key = "pes_kpi_summary"
    now = time.time()
    if not force_refresh:
        hit = _mem_cache.get(mem_key)
        if hit and now - float(hit.get("_ts", 0)) < ttl:
            payload = dict(hit["payload"])
            payload["cache"] = "memory"
            return payload

    Path(cdir).mkdir(parents=True, exist_ok=True)
    cache_file, meta_file = _pes_summary_cache_paths(cdir)
    if not force_refresh and cache_file.is_file() and meta_file.is_file():
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
            age = now - float(m.get("fetched_epoch", 0))
            if age < ttl:
                payload = json.loads(cache_file.read_text(encoding="utf-8"))
                payload["cache"] = "disk"
                payload["cache_age_s"] = int(age)
                _mem_cache[mem_key] = {"_ts": now, "payload": payload}
                return payload
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    fetched_at = datetime.now(timezone.utc).isoformat()
    errors: list[str] = []
    escasez_feats: list[dict[str, Any]] = []
    sequia_feats: list[dict[str, Any]] = []

    esc_url = build_wfs_getfeature_url(
        f"{CHG_WORKSPACE}:pes_estado_escasez",
        property_name="cod_ute,nom_ute,indicador,escenario,fecha",
    )
    seq_url = build_wfs_getfeature_url(
        f"{CHG_WORKSPACE}:pes_estado_sequia",
        property_name="cod_szona,nom_szona,indice,estado,fecha",
    )
    try:
        esc_fc = _http_get_json(esc_url)
        escasez_feats = list(esc_fc.get("features") or [])
    except Exception as exc:  # noqa: BLE001
        errors.append(f"escasez: {exc}")
    try:
        seq_fc = _http_get_json(seq_url)
        sequia_feats = list(seq_fc.get("features") or [])
    except Exception as exc:  # noqa: BLE001
        errors.append(f"sequia: {exc}")

    # Stale fallback if both failed
    if not escasez_feats and not sequia_feats and cache_file.is_file():
        try:
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            payload["cache"] = "stale_disk"
            payload["error"] = "; ".join(errors) if errors else "fetch fallido"
            _mem_cache[mem_key] = {"_ts": now, "payload": payload}
            return payload
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    escasez = summarize_pes_features(escasez_feats, kind="escasez")
    sequia = summarize_pes_features(sequia_feats, kind="sequia")
    as_of = escasez.get("as_of") or sequia.get("as_of")
    payload: dict[str, Any] = {
        "available": bool(escasez.get("available") or sequia.get("available")),
        "as_of": as_of,
        "fetched_at": fetched_at,
        "cache": "network",
        "attribution": ATTRIBUTION_ES,
        "provider": "CHG PES (Plan Especial de Sequías)",
        "note_es": (
            "Resumen regional del PES CHG (escasez por UTE y sequía por zona). "
            "Solo propiedades vía WFS (sin geometrías). Destaca UTEs/zonas del "
            "entorno Doñana / Huelva–Sevilla. No es ICRA."
        ),
        "caveat_es": (
            "Escenarios del Plan Especial de Sequías; no sustituye resoluciones "
            "oficiales de restricción ni el inventario ICRA."
        ),
        "escasez": escasez,
        "sequia": sequia,
        "source_urls": {"escasez": esc_url, "sequia": seq_url},
        "error": "; ".join(errors) if errors else None,
    }
    try:
        cache_file.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        meta_file.write_text(
            json.dumps(
                {
                    "fetched_at": fetched_at,
                    "fetched_epoch": now,
                    "as_of": as_of,
                    "escasez_n": escasez.get("feature_count"),
                    "sequia_n": sequia.get("feature_count"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass
    _mem_cache[mem_key] = {"_ts": now, "payload": payload}
    return payload


def caveats_es() -> list[str]:
    return [
        "Capas públicas de la IDE-CHG (GeoServer). No se consultan portales privados de comunidades de regantes.",
        "CRS nativo habitual EPSG:25830; el API reproyecta a EPSG:4326 vía parámetro srsName del WFS.",
        "Las geometrías vectoriales se simplifican para el mapa web (tolerancia ~0,005° ≈ 500 m; PES ~0,01°): no usar para catastro ni deslindes.",
        "recintos_riego_pub tiene cientos de miles de polígonos; la vista cartográfica usa WMS. Una descarga GeoJSON completa saturaría el navegador.",
        "PES sequía/escasez: escenarios oficiales del Plan Especial de Sequías CHG. No es ICRA ni la zonificación REDIAM Doñana.",
        "Piezómetros: solo ubicación/metadatos; las series históricas están en el visor IDE-CHG (no se scrapean).",
        "WFS 2.0 GetFeature puede devolver 401 en este servidor; el cliente usa WFS 1.1.0.",
        "La actualización CHG es aproximadamente mensual; la caché local evita martillar el GeoServer en cada carga del dashboard.",
        "Atribución: Confederación Hidrográfica del Guadalquivir (CHG) / datos.gob.es.",
    ]


def build_wfs_getfeature_url(
    type_name: str,
    *,
    base: str = CHG_WFS_BASE,
    version: str = WFS_VERSION,
    output_format: str = "application/json",
    srs_name: str = DEFAULT_SRS,
    max_features: int | None = None,
    bbox: str | None = None,
    property_name: str | None = None,
) -> str:
    """Build a WFS 1.1.0 GetFeature URL (pure function — unit-tested)."""
    params: dict[str, str] = {
        "service": "WFS",
        "version": version,
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": output_format,
        "srsName": srs_name,
    }
    if max_features is not None:
        params["maxFeatures"] = str(int(max_features))
    if bbox:
        params["bbox"] = bbox
    if property_name:
        params["propertyName"] = property_name
    return f"{base.rstrip('?')}?{urllib.parse.urlencode(params)}"


def build_wms_leaflet_config(layer_id: str = "recintos_riego_pub") -> dict[str, Any]:
    meta = LAYER_BY_ID.get(layer_id) or LAYER_BY_ID["recintos_riego_pub"]
    return {
        "url": meta.get("wms_url") or CHG_WMS_BASE,
        "layers": meta.get("wms_layers") or meta["type_name"],
        "format": "image/png",
        "transparent": True,
        "version": "1.1.1",
        "attribution": ATTRIBUTION_HTML,
        "uppercase": False,
    }


def _perp_dist(p: list[float], a: list[float], b: list[float]) -> float:
    x, y = p[0], p[1]
    x1, y1 = a[0], a[1]
    x2, y2 = b[0], b[1]
    dx, dy = x2 - x1, y2 - y1
    if dx == 0.0 and dy == 0.0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def douglas_peucker(pts: list[list[float]], tol: float) -> list[list[float]]:
    """Simplify a polyline/ring (pure function). Preserves closed rings."""
    if tol <= 0 or len(pts) < 3:
        return pts
    closed = pts[0] == pts[-1]
    work = pts[:-1] if closed and len(pts) > 1 else pts
    if len(work) < 3:
        return pts
    keep = [False] * len(work)
    keep[0] = keep[-1] = True
    stack: list[tuple[int, int]] = [(0, len(work) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = work[i], work[j]
        max_d = -1.0
        idx = -1
        for k in range(i + 1, j):
            d = _perp_dist(work[k], a, b)
            if d > max_d:
                max_d = d
                idx = k
        if max_d > tol and idx >= 0:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    out = [work[i] for i in range(len(work)) if keep[i]]
    if closed:
        if not out:
            return pts
        if out[0] != out[-1]:
            out.append(list(out[0]))
        # Degenerate ring → keep original
        if len(out) < 4:
            return pts
    elif len(out) < 2:
        return pts
    return out


def simplify_geometry(
    geometry: dict[str, Any] | None,
    tol: float = DEFAULT_SIMPLIFY_TOL_DEG,
) -> dict[str, Any] | None:
    """Return a shallow-copied geometry with simplified coordinates."""
    if not geometry or tol <= 0:
        return geometry
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype is None or coords is None:
        return geometry

    def simp_line(line: list) -> list:
        pts = [[float(p[0]), float(p[1])] for p in line]
        return douglas_peucker(pts, tol)

    if gtype == "LineString":
        new_coords = simp_line(coords)
    elif gtype == "MultiLineString":
        new_coords = [simp_line(ls) for ls in coords]
    elif gtype == "Polygon":
        new_coords = [simp_line(ring) for ring in coords]
    elif gtype == "MultiPolygon":
        new_coords = [[simp_line(ring) for ring in poly] for poly in coords]
    else:
        return geometry
    return {"type": gtype, "coordinates": new_coords}


def simplify_feature_collection(
    fc: dict[str, Any],
    tol: float = DEFAULT_SIMPLIFY_TOL_DEG,
) -> dict[str, Any]:
    """Simplify all feature geometries in a GeoJSON FeatureCollection."""
    features_out: list[dict[str, Any]] = []
    for feat in fc.get("features") or []:
        if not isinstance(feat, dict):
            continue
        geom = simplify_geometry(feat.get("geometry"), tol)
        features_out.append(
            {
                "type": "Feature",
                "id": feat.get("id"),
                "properties": feat.get("properties") or {},
                "geometry": geom,
            }
        )
    out: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": features_out,
    }
    if "crs" in fc:
        out["crs"] = fc["crs"]
    if "totalFeatures" in fc:
        out["totalFeatures"] = fc["totalFeatures"]
    return out


def count_coordinate_points(geometry: dict[str, Any] | None) -> int:
    if not geometry:
        return 0

    def walk(c: Any) -> int:
        if not c:
            return 0
        if isinstance(c[0], (int, float)):
            return 1
        return sum(walk(i) for i in c)

    return walk(geometry.get("coordinates"))


def _cache_path(layer_id: str, cache_dir: str) -> Path:
    return Path(cache_dir) / f"{layer_id}.geojson"


def _meta_path(layer_id: str, cache_dir: str) -> Path:
    return Path(cache_dir) / f"{layer_id}.meta.json"


def _http_get_json(url: str, *, timeout: float = HTTP_TIMEOUT_S) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json, application/geo+json, */*",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("WFS response is not a JSON object")
            if data.get("type") != "FeatureCollection" and "features" not in data:
                # GeoServer sometimes returns ServiceExceptionReport as JSON-ish text
                raise ValueError(f"Unexpected WFS payload keys: {list(data)[:8]}")
            return data
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
            last_err = exc
            if attempt < HTTP_RETRIES:
                time.sleep(0.6 * attempt)
    assert last_err is not None
    raise last_err


def fetch_layer_geojson(
    layer_id: str,
    *,
    force_refresh: bool = False,
    cache_dir: str | None = None,
    cache_ttl_s: int | None = None,
    simplify_tol: float | None = None,
    max_features: int | None = None,
    bbox: str | None = None,
) -> dict[str, Any]:
    """Fetch (or cache-read) a CHG layer as simplified GeoJSON + metadata envelope."""
    meta = LAYER_BY_ID.get(layer_id)
    if meta is None:
        raise KeyError(f"Unknown CHG layer: {layer_id}")

    cdir = cache_dir or DEFAULT_CACHE_DIR
    ttl = DEFAULT_CACHE_TTL_S if cache_ttl_s is None else cache_ttl_s
    if simplify_tol is not None:
        tol = simplify_tol
    elif meta.get("simplify_tol_deg") is not None:
        tol = float(meta["simplify_tol_deg"])
    else:
        tol = DEFAULT_SIMPLIFY_TOL_DEG
    # Sample/bounded requests skip shared disk cache (different payload).
    use_disk = bbox is None and max_features is None
    mf = max_features if max_features is not None else meta.get("max_features")

    # Recintos full dump is forbidden — require explicit max_features or bbox.
    if layer_id == "recintos_riego_pub" and bbox is None and max_features is None:
        return {
            "available": False,
            "layer_id": layer_id,
            "type_name": meta["type_name"],
            "render": "wms",
            "wms": build_wms_leaflet_config(layer_id),
            "feature_collection": {"type": "FeatureCollection", "features": []},
            "feature_count": 0,
            "feature_count_source": meta.get("feature_count_hint"),
            "simplified": False,
            "simplify_tol_deg": None,
            "fetched_at": None,
            "cache": "skipped",
            "source_url": build_wfs_getfeature_url(meta["type_name"], max_features=1),
            "attribution": ATTRIBUTION_ES,
            "crs": DEFAULT_SRS,
            "note_es": meta.get("note_es"),
            "error": (
                "recintos_riego_pub completo (~349k features) no se sirve como GeoJSON. "
                "Use WMS (wms.*) o pase maxFeatures / bbox."
            ),
        }

    now = time.time()
    mem_key = f"{layer_id}|tol={tol}|mf={mf}|bbox={bbox}"
    if not force_refresh:
        hit = _mem_cache.get(mem_key)
        if hit and now - float(hit.get("_ts", 0)) < ttl:
            payload = dict(hit["payload"])
            payload["cache"] = "memory"
            return payload

    Path(cdir).mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(layer_id, cdir)
    meta_file = _meta_path(layer_id, cdir)

    if use_disk and not force_refresh and cache_file.is_file() and meta_file.is_file():
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
            age = now - float(m.get("fetched_epoch", 0))
            if age < ttl and abs(float(m.get("simplify_tol_deg", -1)) - tol) < 1e-12:
                fc = json.loads(cache_file.read_text(encoding="utf-8"))
                payload = {
                    "available": True,
                    "layer_id": layer_id,
                    "type_name": meta["type_name"],
                    "render": meta.get("render"),
                    "wms": build_wms_leaflet_config(layer_id)
                    if meta.get("render") == "wms"
                    else None,
                    "feature_collection": fc,
                    "feature_count": len(fc.get("features") or []),
                    "feature_count_source": m.get("total_features"),
                    "simplified": bool(meta.get("simplify")),
                    "simplify_tol_deg": tol if meta.get("simplify") else None,
                    "point_count": m.get("point_count"),
                    "fetched_at": m.get("fetched_at"),
                    "cache": "disk",
                    "cache_age_s": int(age),
                    "source_url": m.get("source_url"),
                    "attribution": ATTRIBUTION_ES,
                    "crs": DEFAULT_SRS,
                    "note_es": meta.get("note_es"),
                    "error": None,
                }
                _mem_cache[mem_key] = {"_ts": now, "payload": payload}
                return payload
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    url = build_wfs_getfeature_url(
        meta["type_name"],
        max_features=int(mf) if mf is not None else None,
        bbox=bbox,
    )
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        raw_fc = _http_get_json(url)
    except Exception as exc:  # noqa: BLE001 — surface as soft failure
        # Stale disk fallback
        if use_disk and cache_file.is_file():
            try:
                fc = json.loads(cache_file.read_text(encoding="utf-8"))
                m = {}
                if meta_file.is_file():
                    m = json.loads(meta_file.read_text(encoding="utf-8"))
                payload = {
                    "available": True,
                    "layer_id": layer_id,
                    "type_name": meta["type_name"],
                    "render": meta.get("render"),
                    "wms": build_wms_leaflet_config(layer_id)
                    if meta.get("render") == "wms"
                    else None,
                    "feature_collection": fc,
                    "feature_count": len(fc.get("features") or []),
                    "feature_count_source": m.get("total_features"),
                    "simplified": bool(meta.get("simplify")),
                    "simplify_tol_deg": m.get("simplify_tol_deg"),
                    "point_count": m.get("point_count"),
                    "fetched_at": m.get("fetched_at"),
                    "cache": "stale_disk",
                    "source_url": url,
                    "attribution": ATTRIBUTION_ES,
                    "crs": DEFAULT_SRS,
                    "note_es": meta.get("note_es"),
                    "error": f"Fetch fallido ({exc}); sirviendo caché antigua.",
                }
                _mem_cache[mem_key] = {"_ts": now, "payload": payload}
                return payload
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        return {
            "available": False,
            "layer_id": layer_id,
            "type_name": meta["type_name"],
            "render": meta.get("render"),
            "wms": build_wms_leaflet_config(layer_id)
            if meta.get("render") == "wms"
            else None,
            "feature_collection": {"type": "FeatureCollection", "features": []},
            "feature_count": 0,
            "fetched_at": fetched_at,
            "cache": "miss",
            "source_url": url,
            "attribution": ATTRIBUTION_ES,
            "crs": DEFAULT_SRS,
            "note_es": meta.get("note_es"),
            "error": str(exc),
        }

    total_features = raw_fc.get("totalFeatures") or raw_fc.get("numberMatched")
    if meta.get("simplify"):
        fc = simplify_feature_collection(raw_fc, tol=tol)
    else:
        fc = {
            "type": "FeatureCollection",
            "features": list(raw_fc.get("features") or []),
        }
        if "crs" in raw_fc:
            fc["crs"] = raw_fc["crs"]

    point_count = sum(
        count_coordinate_points(f.get("geometry")) for f in (fc.get("features") or [])
    )

    if use_disk:
        try:
            cache_file.write_text(
                json.dumps(fc, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            meta_file.write_text(
                json.dumps(
                    {
                        "layer_id": layer_id,
                        "fetched_at": fetched_at,
                        "fetched_epoch": now,
                        "simplify_tol_deg": tol if meta.get("simplify") else None,
                        "total_features": total_features,
                        "feature_count": len(fc.get("features") or []),
                        "point_count": point_count,
                        "source_url": url,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass

    payload = {
        "available": True,
        "layer_id": layer_id,
        "type_name": meta["type_name"],
        "render": meta.get("render"),
        "wms": build_wms_leaflet_config(layer_id)
        if meta.get("render") == "wms"
        else None,
        "feature_collection": fc,
        "feature_count": len(fc.get("features") or []),
        "feature_count_source": total_features,
        "simplified": bool(meta.get("simplify")),
        "simplify_tol_deg": tol if meta.get("simplify") else None,
        "point_count": point_count,
        "fetched_at": fetched_at,
        "cache": "network",
        "source_url": url,
        "attribution": ATTRIBUTION_ES,
        "crs": DEFAULT_SRS,
        "note_es": meta.get("note_es"),
        "error": None,
    }
    _mem_cache[mem_key] = {"_ts": now, "payload": payload}
    return payload


def build_chg_layers_snapshot(
    *,
    include_inline_geojson: bool = False,
    include_pes_kpi: bool = True,
) -> dict[str, Any]:
    """Dashboard metadata block under irrigation_autonomy.chg_layers.

    By default does NOT fetch full GeoJSON (avoids hammering / bloating
    /api/dashboard). Map UI loads GeoJSON/WMS lazily via dedicated endpoints.
    Optionally attaches a lightweight PES KPI (properties-only WFS, ~5 KB,
    cached 24 h) for Resumen / Risk cards.
    """
    layers_out: list[dict[str, Any]] = []
    for L in _layer_catalog():
        entry = {
            "id": L["id"],
            "type_name": L["type_name"],
            "title_es": L["title_es"],
            "title_en": L.get("title_en"),
            "render": L["render"],
            "endpoint": L.get("endpoint"),
            "feature_count_hint": L.get("feature_count_hint"),
            "enabled_default": L.get("enabled_default", False),
            "priority": L.get("priority", 9),
            "note_es": L.get("note_es"),
            "group": L.get("group"),
            "style_mode": L.get("style_mode"),
            "wms": build_wms_leaflet_config(L["id"]) if L["render"] == "wms" else None,
        }
        if L.get("datos_gob_es"):
            entry["datos_gob_es"] = L["datos_gob_es"]
        if L.get("highlight_provinces"):
            entry["highlight_provinces"] = L["highlight_provinces"]
        if L.get("series_url"):
            entry["series_url"] = L["series_url"]
        if L.get("series_note_es"):
            entry["series_note_es"] = L["series_note_es"]
        if L.get("simplify_tol_deg") is not None:
            entry["simplify_tol_deg"] = L["simplify_tol_deg"]
        if include_inline_geojson and L["render"] == "geojson" and L["id"] in (
            "sistemas_explotacion",
            "patrimonio_zonas_regables",
            "balsas",
            "zonas_sobreexplotadas",
        ):
            try:
                payload = fetch_layer_geojson(L["id"])
                entry["geojson"] = payload.get("feature_collection")
                entry["fetched_at"] = payload.get("fetched_at")
                entry["available"] = payload.get("available")
            except Exception as exc:  # noqa: BLE001
                entry["available"] = False
                entry["error"] = str(exc)
        layers_out.append(entry)

    pes_kpi: dict[str, Any] | None = None
    if include_pes_kpi:
        try:
            pes_kpi = fetch_pes_kpi_summary()
        except Exception as exc:  # noqa: BLE001 — never break catalog
            pes_kpi = {
                "available": False,
                "error": str(exc),
                "escasez": {"available": False, "counts_by_escenario": {}},
                "sequia": {"available": False, "counts_by_estado": {}},
            }

    as_of = (pes_kpi or {}).get("as_of")
    fetched_at = (pes_kpi or {}).get("fetched_at")

    return {
        "available": True,
        "provider": "CHG IDE-CHG GeoServer",
        "attribution": ATTRIBUTION_ES,
        "attribution_html": ATTRIBUTION_HTML,
        "base_wfs": CHG_WFS_BASE,
        "base_wms": CHG_WMS_BASE,
        "crs_request": DEFAULT_SRS,
        "crs_native_typical": "EPSG:25830",
        "wfs_version": WFS_VERSION,
        "cache_ttl_s": DEFAULT_CACHE_TTL_S,
        "simplify_tol_deg": DEFAULT_SIMPLIFY_TOL_DEG,
        "pes_simplify_tol_deg": PES_SIMPLIFY_TOL_DEG,
        "as_of": as_of,
        "fetched_at": fetched_at,
        "lazy": True,
        "note_es": (
            "Capas abiertas de la Confederación Hidrográfica del Guadalquivir "
            "(sistemas, recintos WMS, balsas, dotación olivar, zonas "
            "sobreexplotadas/vulnerables, PES sequía/escasez, piezómetros). "
            "El dashboard expone metadatos + KPI PES ligero (sin geometrías); "
            "el mapa carga WMS/GeoJSON bajo demanda con caché en disco "
            "(TTL 24 h). Escenarios PES ≠ ICRA."
        ),
        "caveats_es": caveats_es(),
        "layers": layers_out,
        "pes_kpi": pes_kpi,
    }
