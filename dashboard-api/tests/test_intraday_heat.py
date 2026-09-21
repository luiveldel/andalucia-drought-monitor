"""Unit tests for intradaily heat spikes (SiAR hourly / Open-Meteo proxy)."""

from __future__ import annotations

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

import app.intraday_heat as ih  # noqa: E402


def _first(*names):
    for n in names:
        if hasattr(ih, n):
            return getattr(ih, n)
    raise AttributeError(names)


def test_hour_flags_thresholds():
    flags = _first("_hour_flags", "_hour_flags")
    heat_t = _first("HEAT_TEMP_C", "HEAT_TEMP_C")
    heat_rh = _first("HEAT_RH_PCT", "HEAT_RH_PCT")
    assert flags(36.0, 20.0)[0] is True
    assert flags(36.0, 40.0)[0] is False
    assert flags(33.0, 20.0)[1] is True
    assert flags(30.0, 20.0) == (False, False)
    assert float(heat_t) == 35.0 and float(heat_rh) == 30.0


def test_parse_hora_min_siar():
    parse = _first("_parse_hora_min", "_parse_hora_min", "_parse_siar_hora_min")
    assert parse(30) == (0, 30)
    assert parse(100) == (1, 0)
    assert parse(1330) == (13, 30)


def test_summarize_peak_vs_mean_plain_language():
    flags = _first("_hour_flags", "_hour_flags")
    summarize = _first("_summarize_hours", "_summarize_hours")
    hours = []
    for h in range(24):
        temp = 28.0 + (12.0 if 14 <= h <= 17 else 0.0)
        rh = 25.0 if temp >= 36 else 45.0
        heat, elev = flags(temp, rh)
        hours.append(
            {
                "date": "2026-07-15",
                "time": f"2026-07-15T{h:02d}:00",
                "hour_label": f"{h:02d}:00",
                "temp_c": temp,
                "humidity_pct": rh,
                "et0_mm": 0.2,
                "radiation": 500.0 if 10 <= h <= 18 else 0.0,
                "stations": 1,
                "heat_stress": heat,
                "elevated_heat": elev,
            }
        )
    # kwargs may be province_name/location_label
    try:
        summary = summarize(hours, province_name="Sevilla", location_label="Sevilla test")
    except TypeError:
        summary = summarize(hours, province_name="Sevilla", location_label="Sevilla test")
    assert summary["heat_hours"] >= 1
    assert summary["temp_peak_c"] == 40.0
    assert summary["peak_minus_mean_c"] is not None and summary["peak_minus_mean_c"] > 0
    plain = summary["plain_es"].lower()
    assert "pico" in plain or "media" in plain


def test_open_meteo_proxy_live_or_empty():
    build = _first("build_intraday_heat", "build_intraday_heat")
    try:
        payload = build(None, lookback_days=1)
    except TypeError:
        payload = build(None, lookback_days=1)
    assert "available" in payload
    assert "source" in payload
    assert "by_province" in payload
    assert "regional" in payload
    if payload["available"]:
        assert payload["source"] in {"open_meteo_proxy", "siar_hourly"}
        assert payload["regional"] is not None
        assert payload["regional"]["hours_total"] > 0
        assert payload.get("headline_es")
        assert "siar_table" in payload
