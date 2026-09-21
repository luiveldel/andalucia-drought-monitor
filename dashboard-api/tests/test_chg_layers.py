"""Unit tests for CHG WFS URL building and GeoJSON simplification (no network)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chg_layers import (  # noqa: E402
    CHG_WFS_BASE,
    build_chg_layers_snapshot,
    build_wfs_getfeature_url,
    count_coordinate_points,
    douglas_peucker,
    simplify_feature_collection,
    simplify_geometry,
)


def test_build_wfs_url_basic():
    url = build_wfs_getfeature_url("ggiscloud_root:sistemas_explotacion")
    assert url.startswith(CHG_WFS_BASE + "?")
    assert "service=WFS" in url
    assert "version=1.1.0" in url
    assert "request=GetFeature" in url
    assert "typeName=ggiscloud_root%3Asistemas_explotacion" in url
    assert "outputFormat=application%2Fjson" in url
    assert "srsName=EPSG%3A4326" in url
    assert "maxFeatures" not in url


def test_build_wfs_url_max_and_bbox():
    url = build_wfs_getfeature_url(
        "ggiscloud_root:recintos_riego_pub",
        max_features=50,
        bbox="-6,37,-4,38,EPSG:4326",
    )
    assert "maxFeatures=50" in url
    assert "bbox=-6%2C37%2C-4%2C38%2CEPSG%3A4326" in url


def test_douglas_peucker_collinear():
    pts = [[0.0, 0.0], [0.5, 0.0], [1.0, 0.0]]
    out = douglas_peucker(pts, 0.01)
    assert out == [[0.0, 0.0], [1.0, 0.0]]


def test_douglas_peucker_keeps_spike():
    pts = [[0.0, 0.0], [0.5, 1.0], [1.0, 0.0]]
    out = douglas_peucker(pts, 0.1)
    assert len(out) == 3
    out2 = douglas_peucker(pts, 2.0)
    assert out2 == [[0.0, 0.0], [1.0, 0.0]]


def test_douglas_closed_ring():
    ring = [
        [0.0, 0.0],
        [0.0, 1.0],
        [0.5, 1.0],
        [1.0, 1.0],
        [1.0, 0.0],
        [0.0, 0.0],
    ]
    out = douglas_peucker(ring, 0.01)
    assert out[0] == out[-1]
    assert len(out) >= 4


def test_simplify_multipolygon_reduces_points():
    # Dense square-ish ring
    ring = [[i / 100.0, 0.0] for i in range(101)]
    ring += [[1.0, i / 100.0] for i in range(1, 101)]
    ring += [[1.0 - i / 100.0, 1.0] for i in range(1, 101)]
    ring += [[0.0, 1.0 - i / 100.0] for i in range(1, 101)]
    geom = {"type": "MultiPolygon", "coordinates": [[ring]]}
    before = count_coordinate_points(geom)
    simplified = simplify_geometry(geom, tol=0.05)
    after = count_coordinate_points(simplified)
    assert before > 300
    assert after < before
    assert after >= 4


def test_simplify_feature_collection():
    fc = {
        "type": "FeatureCollection",
        "totalFeatures": 1,
        "features": [
            {
                "type": "Feature",
                "id": "x.1",
                "properties": {"nom": "A"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[0, 0], [0.5, 0], [1, 0]],
                },
            }
        ],
    }
    out = simplify_feature_collection(fc, tol=0.01)
    assert out["type"] == "FeatureCollection"
    assert out["totalFeatures"] == 1
    coords = out["features"][0]["geometry"]["coordinates"]
    assert coords == [[0.0, 0.0], [1.0, 0.0]]


def test_snapshot_metadata_no_network():
    snap = build_chg_layers_snapshot(include_inline_geojson=False)
    assert snap["available"] is True
    assert snap["lazy"] is True
    ids = {L["id"] for L in snap["layers"]}
    assert "sistemas_explotacion" in ids
    assert "recintos_riego_pub" in ids
    rec = next(L for L in snap["layers"] if L["id"] == "recintos_riego_pub")
    assert rec["render"] == "wms"
    assert rec["wms"]["layers"].endswith("recintos_riego_pub")
    assert "CHG" in snap["attribution"]
    assert len(snap["caveats_es"]) >= 3


def test_perp_distance_math_sanity():
    # Midpoint offset of an axis-aligned segment
    from app.chg_layers import _perp_dist

    d = _perp_dist([0.5, 1.0], [0.0, 0.0], [1.0, 0.0])
    assert abs(d - 1.0) < 1e-9


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("ALL PASS")
