"""Public irrigation layers beyond CHG: REDIAM (Doñana) WMS + ICRA archive links.

CHG vector extras (dotación olivar, zonas sobreexplotadas/vulnerables) live in
chg_layers.py — same GeoServer. This module covers:

  * REDIAM zonificación plan de regadíos corona forestal Doñana (WMS tiles;
    geographically limited N of Doñana forest crown). TLS to Junta endpoints
    is flaky from some networks → optional GetMap proxy with retries.
  * ICRA Andalucía 2002/2008: download-only from portalrediam (no public WFS
    for the full inventory). Exposed as catalog-link metadata, not a live map.

No private community-of-irrigators portals; no login.
"""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "andalucia-drought-monitor/1.0 (+https://andalucia.luisandresvelazquez.com)"

REDIAM_DONANA_WMS_BASE = (
    "https://www.juntadeandalucia.es/medioambiente/mapwms/"
    "REDIAM_zonificacion_plan_regadios_corona_forestal_donana"
)
# Named layers from GetCapabilities (verified on lavd). Subset for map clarity.
REDIAM_DONANA_LAYERS_DEFAULT = "Ambito_plan,Zona_A,Corredor_ecologico"

HTTP_TIMEOUT_S = float(os.environ.get("OPEN_LAYERS_HTTP_TIMEOUT_S", "45"))
HTTP_RETRIES = int(os.environ.get("OPEN_LAYERS_HTTP_RETRIES", "3"))

REDIAM_ATTRIBUTION_ES = (
    "© REDIAM / Junta de Andalucía — Plan de regadíos corona forestal de Doñana"
)
REDIAM_ATTRIBUTION_HTML = (
    '&copy; <a href="https://www.juntadeandalucia.es/medioambiente/site/rediam" '
    'target="_blank" rel="noopener">REDIAM</a> / Junta de Andalucía'
)

ICRA_DOWNLOAD_2002 = (
    "https://portalrediam.cica.es/descargas?path=%2FInf_archivo%2F10_SISTEMAS_PRODUCTIVOS"
    "%2F02_AGRICULTURA_GANADERIA%2FInventario_Regadios_2002"
)
ICRA_RECORD_2008 = (
    "https://portalrediam.cica.es/geonetwork/srv/api/records/"
    "15f843dd-8ac0-4847-ac8a-ed5c58637b23"
)
ICRA_PORTAL = "https://portalrediam.cica.es/"


def caveats_es() -> list[str]:
    return [
        "Capas públicas REDIAM / portalrediam e ICRA histórico. No se consultan portales privados de comunidades de regantes.",
        "Plan regadíos Doñana (REDIAM): ámbito del Plan Especial al norte de la corona forestal; relevante para Huelva y Sevilla. No es el inventario ICRA completo ni cubre toda Andalucía.",
        "TLS hacia mapwms de la Junta puede fallar desde algunas redes; el API ofrece un proxy GetMap con reintentos.",
        "ICRA 2002/2008 es archivo histórico (shapefile/gpkg descargable): no hay WFS público del inventario completo ni cuotas operativas vigentes.",
        "Atribución: REDIAM / Junta de Andalucía; ICRA vía portalrediam.",
    ]


def build_rediam_donana_wms_config(*, use_proxy: bool = True) -> dict[str, Any]:
    """Leaflet-ready WMS config. Prefer API proxy so server-side TLS retries apply."""
    url = (
        "/api/gis/open/rediam/donana.wms"
        if use_proxy
        else REDIAM_DONANA_WMS_BASE
    )
    return {
        "url": url,
        "layers": REDIAM_DONANA_LAYERS_DEFAULT,
        "format": "image/png",
        "transparent": True,
        "version": "1.1.1",
        "attribution": REDIAM_ATTRIBUTION_HTML,
        "uppercase": False,
        "upstream": REDIAM_DONANA_WMS_BASE,
    }


def build_rediam_getcapabilities_url(
    *, base: str = REDIAM_DONANA_WMS_BASE, version: str = "1.1.1"
) -> str:
    """Pure helper (unit-tested)."""
    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetCapabilities",
        "VERSION": version,
    }
    return f"{base.rstrip('?')}?{urllib.parse.urlencode(params)}"


def build_rediam_getmap_url(
    *,
    base: str = REDIAM_DONANA_WMS_BASE,
    layers: str = REDIAM_DONANA_LAYERS_DEFAULT,
    bbox: str,
    width: int = 256,
    height: int = 256,
    srs: str = "EPSG:3857",
    version: str = "1.1.1",
    format: str = "image/png",
    transparent: bool = True,
) -> str:
    """Pure helper to assemble a WMS 1.1.1 GetMap URL (unit-tested)."""
    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": version,
        "LAYERS": layers,
        "STYLES": "",
        "SRS": srs,
        "BBOX": bbox,
        "WIDTH": str(int(width)),
        "HEIGHT": str(int(height)),
        "FORMAT": format,
        "TRANSPARENT": "TRUE" if transparent else "FALSE",
    }
    return f"{base.rstrip('?')}?{urllib.parse.urlencode(params)}"


def _layer_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "donana_plan_regadios",
            "provider": "rediam",
            "title_es": "Plan regadíos Doñana",
            "title_en": "Doñana irrigation plan",
            "render": "wms",
            "endpoint": "/api/gis/open/rediam/donana.wms",
            "feature_count_hint": None,
            "enabled_default": True,
            "priority": 1,
            "highlight_provinces": ["Huelva", "Sevilla"],
            "geographic_scope_es": (
                "Ámbito del Plan Especial al norte de la corona forestal de Doñana "
                "(relevante para Huelva y Sevilla). No es el inventario ICRA completo "
                "ni cubre toda Andalucía."
            ),
            "note_es": (
                "Zonificación REDIAM del plan de regadíos de la corona forestal de "
                "Doñana (Junta de Andalucía). Capa destacada para el contexto "
                "Huelva–Sevilla. Teselas WMS vía proxy API. Ámbito del Plan Especial "
                "al N de la corona forestal; no es el inventario ICRA completo."
            ),
            "wms": build_rediam_donana_wms_config(use_proxy=True),
            "attribution": REDIAM_ATTRIBUTION_ES,
        },
        {
            "id": "icra_download",
            "provider": "icra",
            "title_es": "ICRA Andalucía (archivo 2002/2008)",
            "title_en": "ICRA Andalusia (2002/2008 archive)",
            "render": "catalog-link",
            "endpoint": None,
            "feature_count_hint": None,
            "enabled_default": False,
            "priority": 9,
            "note_es": (
                "Inventario de regadíos de Andalucía (ICRA): solo descarga "
                "(shapefile/gpkg) desde portalrediam. No hay WFS público del "
                "inventario completo. Es archivo histórico, no cuotas operativas "
                "ni dotaciones vigentes."
            ),
            "links": [
                {
                    "label_es": "Descarga ICRA 2002 (portalrediam)",
                    "url": ICRA_DOWNLOAD_2002,
                },
                {
                    "label_es": "Ficha ICRA 2008 (GeoNetwork)",
                    "url": ICRA_RECORD_2008,
                },
                {
                    "label_es": "Portal REDIAM",
                    "url": ICRA_PORTAL,
                },
            ],
            "caveats_es": [
                "No es una capa cartográfica en vivo del monitor.",
                "Datos históricos (2002 / 2008); no usar como cupo actual de riego.",
            ],
            "attribution": "© REDIAM / Junta de Andalucía — Inventario de regadíos (ICRA)",
        },
    ]


LAYER_BY_ID: dict[str, dict[str, Any]] = {L["id"]: L for L in _layer_catalog()}


def build_open_layers_snapshot() -> dict[str, Any]:
    """Dashboard metadata under irrigation_autonomy.open_layers (lazy, no network)."""
    layers_out: list[dict[str, Any]] = []
    for L in _layer_catalog():
        entry = {
            "id": L["id"],
            "provider": L.get("provider"),
            "title_es": L["title_es"],
            "title_en": L.get("title_en"),
            "render": L["render"],
            "endpoint": L.get("endpoint"),
            "feature_count_hint": L.get("feature_count_hint"),
            "enabled_default": L.get("enabled_default", False),
            "priority": L.get("priority", 9),
            "note_es": L.get("note_es"),
            "geographic_scope_es": L.get("geographic_scope_es"),
            "highlight_provinces": L.get("highlight_provinces"),
            "wms": L.get("wms"),
            "links": L.get("links"),
            "caveats_es": L.get("caveats_es"),
            "attribution": L.get("attribution"),
        }
        layers_out.append(entry)

    return {
        "available": True,
        "provider": "REDIAM / ICRA (portalrediam) + capas CHG extras vía /api/gis/chg",
        "attribution": REDIAM_ATTRIBUTION_ES,
        "attribution_html": REDIAM_ATTRIBUTION_HTML,
        "lazy": True,
        "as_of": None,
        "fetched_at": None,
        "note_es": (
            "Capa destacada: Plan regadíos Doñana (REDIAM) — ámbito Huelva–Sevilla "
            "(corona forestal). También ICRA histórico (solo enlaces) y extras CHG "
            "(dotación olivar, zonas sobreexplotadas/vulnerables) en chg_layers."
        ),
        "caveats_es": caveats_es(),
        "rejected_sources_es": [
            "ICRA completo Andalucía 2002/2008: solo descarga en portalrediam (sin WFS público).",
            "CHG WMS histórico https://idechg.chguadalquivir.es/ogc/wmsregadios → 404.",
            "MAPAMA WMS Regadíos Horizonte 2008: ServiceException / roto al sondear.",
            "DERA_g9_usos_suelo WMS: 404 con ese slug.",
        ],
        "layers": layers_out,
        "groups": {
            "rediam": [L["id"] for L in layers_out if L.get("provider") == "rediam"],
            "icra": [L["id"] for L in layers_out if L.get("provider") == "icra"],
            "chg_extras": [
                "dotacion_olivar",
                "zonas_sobreexplotadas",
                "zonas_vulnerables",
            ],
        },
    }


def proxy_rediam_wms_bytes(query_params: dict[str, str]) -> tuple[bytes, str]:
    """Forward a WMS request to REDIAM with timeouts/retries.

    Returns (body, content_type). Raises on total failure.
    Leaflet WMSTileLayer sends GetMap params; we preserve them and hit upstream.
    """
    params = {str(k): str(v) for k, v in query_params.items() if v is not None}
    if "SERVICE" not in {k.upper() for k in params}:
        params.setdefault("SERVICE", "WMS")
    if "REQUEST" not in {k.upper() for k in params}:
        params.setdefault("REQUEST", "GetMap")
    if not any(k.upper() == "LAYERS" for k in params):
        params["LAYERS"] = REDIAM_DONANA_LAYERS_DEFAULT

    url = f"{REDIAM_DONANA_WMS_BASE.rstrip('?')}?{urllib.parse.urlencode(params)}"

    last_err: Exception | None = None
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "image/png,image/*,*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
                ctype = resp.headers.get("Content-Type") or "image/png"
                body = resp.read()
            if not body:
                raise ValueError("Empty REDIAM WMS response")
            return body, ctype.split(";")[0].strip()
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_err = exc
            if attempt < HTTP_RETRIES:
                time.sleep(0.5 * attempt)
    assert last_err is not None
    raise last_err
