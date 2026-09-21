"""Unit tests for SiAR × embalse linking (no DB / no pytest)."""

from __future__ import annotations

import math
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if "sqlalchemy" not in sys.modules:
    sa = types.ModuleType("sqlalchemy")
    sa.text = lambda x: x
    eng = types.ModuleType("sqlalchemy.engine")

    class Connection:  # noqa: N801
        pass

    eng.Connection = Connection
    sys.modules["sqlalchemy"] = sa
    sys.modules["sqlalchemy.engine"] = eng

from app.station_reservoir_links import (  # noqa: E402
    MAX_LINK_DISTANCE_KM,
    haversine_km,
    link_stations,
    parse_siar_coord,
    parse_utm_point_wkt,
    utm_to_latlon,
)


def test_parse_siar_dms_and_decimal():
    assert abs(parse_siar_coord("37º 25' 12'' N") - 37.42) < 1e-6
    assert abs(parse_siar_coord("5º 58' 30'' O", is_lon=True) - (-5.975)) < 1e-6
    assert abs(parse_siar_coord("-5.975", is_lon=True) - (-5.975)) < 1e-9
    assert abs(parse_siar_coord("5.975", is_lon=True) - (-5.975)) < 1e-9
    assert parse_siar_coord(None) is None
    assert parse_siar_coord("") is None


def test_utm_tranco_de_beas():
    lat, lon = utm_to_latlon(517872.95877672, 4225187.8985257, zone=30)
    assert 38.15 < lat < 38.20
    assert -2.85 < lon < -2.75


def test_parse_utm_point():
    assert parse_utm_point_wkt("POINT (517872.95877672 4225187.8985257)") == (
        517872.95877672,
        4225187.8985257,
    )
    assert parse_utm_point_wkt(None) is None


def test_haversine_zero():
    assert haversine_km(37.0, -5.0, 37.0, -5.0) == 0.0
    d = haversine_km(37.0, -5.0, 37.1, -5.0)
    assert 10 < d < 12


def test_link_nearest_and_fallback():
    reservoirs = [
        {
            "reservoir_code": "E01",
            "reservoir_name": "Cerca",
            "province_name": "Sevilla",
            "exploitation_system": "VIAR",
            "watershed_demarcation": "Guadalquivir",
            "lat": 37.50,
            "lon": -5.90,
            "capacity_hm3": 100.0,
        },
        {
            "reservoir_code": "E02",
            "reservoir_name": "Grande",
            "province_name": "Sevilla",
            "exploitation_system": "SISTEMA DE REGULACIÓN GENERAL",
            "watershed_demarcation": "Guadalquivir",
            "lat": 37.80,
            "lon": -5.50,
            "capacity_hm3": 500.0,
        },
    ]
    stations = [
        {
            "station_code": "SE01",
            "station_name": "Cerca SE",
            "province_name": "Sevilla",
            "lat": 37.51,
            "lon": -5.91,
        },
        {
            "station_code": "SE99",
            "station_name": "Lejos",
            "province_name": "Sevilla",
            "lat": 36.0,
            "lon": -7.5,
        },
        {
            "station_code": "XX00",
            "station_name": "Sin coords",
            "province_name": "Sevilla",
            "lat": None,
            "lon": None,
        },
    ]
    linked, counts = link_stations(stations, reservoirs, max_km=MAX_LINK_DISTANCE_KM)
    by_code = {s["station_code"]: s for s in linked}
    assert by_code["SE01"]["link_method"] == "nearest_reservoir"
    assert by_code["SE01"]["reservoir_code"] == "E01"
    assert by_code["SE01"]["distance_km"] is not None
    assert by_code["SE01"]["distance_km"] < 5
    assert by_code["SE99"]["link_method"] == "province_dominant_system"
    assert by_code["SE99"]["exploitation_system"] == "SISTEMA DE REGULACIÓN GENERAL"
    assert by_code["SE99"]["reservoir_code"] is None
    assert by_code["XX00"]["link_method"] == "province_dominant_system"
    assert counts["nearest"] == 1
    assert counts["province_fallback"] == 2
    assert counts["unlinked"] == 0
    assert MAX_LINK_DISTANCE_KM == 80.0
    assert math.isfinite(by_code["SE01"]["distance_km"])


if __name__ == "__main__":
    test_parse_siar_dms_and_decimal()
    test_utm_tranco_de_beas()
    test_parse_utm_point()
    test_haversine_zero()
    test_link_nearest_and_fallback()
    print("OK")

def test_parse_siar_coord_packed_dms():
    from app.station_reservoir_links import parse_siar_coord

    assert abs(parse_siar_coord("365007000N") - 36.83527777777778) < 1e-6
    assert abs(parse_siar_coord("022408000W", is_lon=True) - (-2.402222222222222)) < 1e-6
    assert abs(parse_siar_coord("370528000N") - 37.09111111111111) < 1e-6

