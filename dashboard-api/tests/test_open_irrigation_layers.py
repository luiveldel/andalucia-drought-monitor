"""Unit tests for REDIAM/ICRA open irrigation layer helpers (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.open_irrigation_layers import (  # noqa: E402
    REDIAM_DONANA_LAYERS_DEFAULT,
    REDIAM_DONANA_WMS_BASE,
    build_open_layers_snapshot,
    build_rediam_donana_wms_config,
    build_rediam_getcapabilities_url,
    build_rediam_getmap_url,
)


def test_getcapabilities_url():
    url = build_rediam_getcapabilities_url()
    assert url.startswith(REDIAM_DONANA_WMS_BASE + "?")
    assert "SERVICE=WMS" in url
    assert "REQUEST=GetCapabilities" in url
    assert "VERSION=1.1.1" in url


def test_getmap_url():
    url = build_rediam_getmap_url(
        bbox="-700000,4400000,-600000,4500000",
        width=256,
        height=256,
        srs="EPSG:3857",
    )
    assert url.startswith(REDIAM_DONANA_WMS_BASE + "?")
    assert "REQUEST=GetMap" in url
    assert "LAYERS=" in url
    assert REDIAM_DONANA_LAYERS_DEFAULT.split(",")[0] in url or "Ambito_plan" in url
    assert "WIDTH=256" in url
    assert "HEIGHT=256" in url
    assert "TRANSPARENT=TRUE" in url
    assert "BBOX=-700000%2C4400000%2C-600000%2C4500000" in url


def test_wms_config_uses_proxy_by_default():
    cfg = build_rediam_donana_wms_config()
    assert cfg["url"] == "/api/gis/open/rediam/donana.wms"
    assert cfg["layers"] == REDIAM_DONANA_LAYERS_DEFAULT
    assert cfg["format"] == "image/png"
    assert cfg["transparent"] is True
    assert "upstream" in cfg
    cfg2 = build_rediam_donana_wms_config(use_proxy=False)
    assert cfg2["url"] == REDIAM_DONANA_WMS_BASE


def test_snapshot_metadata_no_network():
    snap = build_open_layers_snapshot()
    assert snap["available"] is True
    assert snap["lazy"] is True
    ids = {L["id"] for L in snap["layers"]}
    assert "donana_plan_regadios" in ids
    assert "icra_download" in ids
    donana = next(L for L in snap["layers"] if L["id"] == "donana_plan_regadios")
    assert donana["render"] == "wms"
    assert donana["enabled_default"] is True
    assert donana["wms"]["url"].endswith("donana.wms")
    assert "Doñana" in (donana.get("title_es") or "")
    assert "Huelva" in (donana.get("highlight_provinces") or [])
    assert "Sevilla" in (donana.get("highlight_provinces") or [])
    icra = next(L for L in snap["layers"] if L["id"] == "icra_download")
    assert icra["render"] == "catalog-link"
    assert isinstance(icra.get("links"), list) and len(icra["links"]) >= 2
    assert "portalrediam" in (icra["links"][0]["url"] or "")
    assert "chg_extras" in snap["groups"]
    assert "dotacion_olivar" in snap["groups"]["chg_extras"]
    assert len(snap["caveats_es"]) >= 3
    assert len(snap["rejected_sources_es"]) >= 2
    assert "REDIAM" in snap["attribution"] or "Junta" in snap["attribution"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("ALL PASS")
