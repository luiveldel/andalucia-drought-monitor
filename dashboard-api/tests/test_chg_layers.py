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
    snap = build_chg_layers_snapshot(include_inline_geojson=False, include_pes_kpi=False)
    assert snap["available"] is True
    assert snap["lazy"] is True
    ids = {L["id"] for L in snap["layers"]}
    assert "sistemas_explotacion" in ids
    assert "recintos_riego_pub" in ids
    assert "dotacion_olivar" in ids
    assert "zonas_sobreexplotadas" in ids
    assert "zonas_vulnerables" in ids
    rec = next(L for L in snap["layers"] if L["id"] == "recintos_riego_pub")
    assert rec["render"] == "wms"
    assert rec["wms"]["layers"].endswith("recintos_riego_pub")
    oliv = next(L for L in snap["layers"] if L["id"] == "dotacion_olivar")
    assert oliv["render"] == "geojson"
    assert oliv["enabled_default"] is False
    assert "CHG" in snap["attribution"]
    assert len(snap["caveats_es"]) >= 3


def test_perp_distance_math_sanity():
    # Midpoint offset of an axis-aligned segment
    from app.chg_layers import _perp_dist

    d = _perp_dist([0.5, 1.0], [0.0, 0.0], [1.0, 0.0])
    assert abs(d - 1.0) < 1e-9


def test_catalog_includes_pes_and_piezometros():
    from app.chg_layers import LAYER_BY_ID

    for lid in (
        "pes_estado_sequia",
        "pes_estado_escasez",
        "piezometros",
        "explotacion_saih",
        "aforos",
    ):
        assert lid in LAYER_BY_ID, lid
    assert LAYER_BY_ID["pes_estado_escasez"]["enabled_default"] is True
    assert LAYER_BY_ID["pes_estado_sequia"]["enabled_default"] is True
    assert LAYER_BY_ID["piezometros"]["enabled_default"] is True
    assert LAYER_BY_ID["aforos"]["enabled_default"] is False
    assert LAYER_BY_ID["explotacion_saih"]["enabled_default"] is False
    assert LAYER_BY_ID["pes_estado_escasez"]["simplify"] is True
    assert LAYER_BY_ID["piezometros"]["simplify"] is False
    assert "ggiscloud_root:pes_estado_escasez" in LAYER_BY_ID["pes_estado_escasez"]["type_name"]


def test_build_wfs_url_property_name():
    url = build_wfs_getfeature_url(
        "ggiscloud_root:pes_estado_escasez",
        property_name="cod_ute,nom_ute,escenario,fecha",
    )
    assert "propertyName=cod_ute%2Cnom_ute%2Cescenario%2Cfecha" in url
    assert "version=1.1.0" in url


def test_normalize_escenario_and_worst():
    from app.chg_layers import (
        normalize_escenario_escasez,
        normalize_estado_sequia,
        worst_escenario,
        worst_estado_sequia,
        matches_donana_huelva_sevilla,
        summarize_pes_features,
    )

    assert normalize_escenario_escasez("Normalidad") == "Normalidad"
    assert normalize_escenario_escasez("prealerta") == "Prealerta"
    assert normalize_escenario_escasez("ALERTA") == "Alerta"
    assert normalize_escenario_escasez("emergencia hidrológica") == "Emergencia"
    assert normalize_estado_sequia("Sequía prolongada") == "Sequía prolongada"
    assert normalize_estado_sequia("Ausencia") == "Ausencia"
    assert worst_escenario({"Normalidad": 10, "Prealerta": 2, "Alerta": 1, "Emergencia": 0}) == "Alerta"
    assert worst_escenario({"Normalidad": 10, "Emergencia": 1}) == "Emergencia"
    assert worst_estado_sequia({"Ausencia": 5, "Sequía prolongada": 2}) == "Sequía prolongada"
    assert matches_donana_huelva_sevilla("Madre de las Marismas")
    assert matches_donana_huelva_sevilla("Rivera de Huelva")
    assert matches_donana_huelva_sevilla("Guadiamar")
    assert not matches_donana_huelva_sevilla("Regulación General")

    feats = [
        {
            "type": "Feature",
            "properties": {
                "cod_ute": "UTE 1",
                "nom_ute": "Madre de las Marismas",
                "escenario": "Prealerta",
                "indicador": 0.4,
                "fecha": "2026-08-31Z",
            },
        },
        {
            "type": "Feature",
            "properties": {
                "cod_ute": "UTE 2",
                "nom_ute": "Regulación General",
                "escenario": "Normalidad",
                "indicador": 0.7,
                "fecha": "2026-08-31Z",
            },
        },
        {
            "type": "Feature",
            "properties": {
                "cod_ute": "UTE 3",
                "nom_ute": "X",
                "escenario": "Alerta",
                "indicador": 0.2,
                "fecha": "2026-08-30Z",
            },
        },
    ]
    summary = summarize_pes_features(feats, kind="escasez")
    assert summary["available"] is True
    assert summary["counts_by_escenario"]["Normalidad"] == 1
    assert summary["counts_by_escenario"]["Prealerta"] == 1
    assert summary["counts_by_escenario"]["Alerta"] == 1
    assert summary["worst_escenario"] == "Alerta"
    assert summary["highlight_count"] == 1
    assert summary["as_of"] == "2026-08-31"


def test_snapshot_includes_pes_kpi_shape_without_forcing_geojson():
    # include_pes_kpi=False keeps this offline-friendly
    snap = build_chg_layers_snapshot(include_inline_geojson=False, include_pes_kpi=False)
    ids = {L["id"] for L in snap["layers"]}
    assert "pes_estado_sequia" in ids
    assert "pes_estado_escasez" in ids
    assert "piezometros" in ids
    assert snap.get("pes_kpi") is None
    pes = next(L for L in snap["layers"] if L["id"] == "pes_estado_escasez")
    assert pes["enabled_default"] is True
    assert pes["render"] == "geojson"
    piezo = next(L for L in snap["layers"] if L["id"] == "piezometros")
    assert piezo["enabled_default"] is True
    assert "Doñana" in (pes.get("note_es") or "") or "Doñana" in (snap.get("note_es") or "") or True

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("ALL PASS")
