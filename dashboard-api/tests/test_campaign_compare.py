"""Unit tests for interannual Apr–Sep campaign compare (no DB / no pytest)."""

from __future__ import annotations

import sys
import types
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

# Allow running as `python dashboard-api/tests/test_campaign_compare.py`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Stub sqlalchemy if missing in the box environment
if "sqlalchemy" not in sys.modules:
    sa = types.ModuleType("sqlalchemy")
    sa.text = lambda x: x
    eng = types.ModuleType("sqlalchemy.engine")

    class Connection:  # noqa: N801
        pass

    eng.Connection = Connection
    sys.modules["sqlalchemy"] = sa
    sys.modules["sqlalchemy.engine"] = eng

from app.campaign_compare import (  # noqa: E402
    MIN_DAYS,
    _accumulate,
    _plain_en,
    _plain_es,
    _safe_through,
    _verdict,
    build_campaign_compare,
)


def test_safe_through_caps_to_campaign_end():
    assert _safe_through(2024, date(2024, 10, 15)) == date(2024, 9, 30)
    assert _safe_through(2024, date(2024, 6, 10)) == date(2024, 6, 10)
    assert _safe_through(2023, date(2026, 9, 20)) == date(2023, 9, 20)


def test_verdict_bands():
    assert _verdict(None) == "unknown"
    assert _verdict(12.0) == "worse"
    assert _verdict(-8.0) == "better"
    assert _verdict(2.0) == "similar"
    assert MIN_DAYS >= 7


def test_plain_language():
    assert "peor" in _plain_es(2022, "worse", 15.0)
    assert "mejor" in _plain_es(2023, "better", -10.0)
    assert "worse" in _plain_en(2022, "worse", 15.0)


def test_accumulate_sums_hm3():
    daily = {
        "Sevilla": [
            {
                "date": "2026-04-01",
                "et0_mm": 5.0,
                "pe_mm": 0.0,
                "precip_mm": 0.0,
                "station_count": 3,
            },
            {
                "date": "2026-04-02",
                "et0_mm": 4.0,
                "pe_mm": 1.0,
                "precip_mm": 1.0,
                "station_count": 3,
            },
        ]
    }
    regional, by_prov, n_days = _accumulate(daily)
    assert n_days == 2
    assert by_prov and by_prov[0]["province_name"] == "Sevilla"
    assert regional["cum_demand_hm3"] is not None
    assert float(regional["cum_demand_hm3"]) > 0


def _fake_rows(conn, sql, **params):
    sql_l = " ".join(sql.lower().split())
    if "greatest(" in sql_l:
        return [{"d": "2026-09-20"}]
    if "min(fecha)" in sql_l and "raw_siar" in sql_l:
        return [{"mn": "2026-06-01", "mx": "2026-09-20"}]
    if "min(fecha)" in sql_l and "raw_ria" in sql_l:
        return [{"mn": "2022-04-01", "mx": "2026-09-19"}]
    if "count(distinct fecha)" in sql_l and "raw_siar" in sql_l:
        start = params.get("start", "")
        return [{"n": 80 if str(start).startswith("2026") else 0}]
    if "count(distinct fecha)" in sql_l and "raw_ria" in sql_l:
        start = str(params.get("start", ""))
        year = int(start[:4]) if start else 0
        return [{"n": 100 if 2022 <= year <= 2026 else 0}]
    if "from raw.raw_siar_clima_diario" in sql_l and "group by fecha" in sql_l:
        rows = []
        for d in range(1, 21):
            for prov in ("Sevilla", "Jaén"):
                rows.append(
                    {
                        "d": f"2026-04-{d:02d}",
                        "province_name": prov,
                        "station_count": 3,
                        "et0_mm": 5.0,
                        "pe_mm": 0.0,
                        "precip_mm": 0.0,
                    }
                )
        return rows
    if "from raw.raw_ria_clima_diario" in sql_l and "group by fecha" in sql_l:
        start = str(params.get("start", "2022-04-01"))
        year = int(start[:4])
        rows = []
        for d in range(1, 21):
            for prov in ("Sevilla", "Jaén"):
                rows.append(
                    {
                        "d": f"{year}-04-{d:02d}",
                        "province_name": prov,
                        "station_count": 3,
                        "et0_mm": 4.0,
                        "pe_mm": 0.5,
                        "precip_mm": 0.5,
                    }
                )
        return rows
    if "max(fecha)" in sql_l:
        return [{"d": "2026-09-20"}]
    return []


def test_build_campaign_compare_mixed_sources():
    conn = MagicMock()
    with patch("app.campaign_compare._rows", side_effect=_fake_rows):
        out = build_campaign_compare(conn, as_of=date(2026, 9, 20))
    assert out["available"] is True
    assert out["current_year"] == 2026
    years = {y["year"]: y for y in out["years"]}
    assert 2026 in years
    assert years[2026]["source"] == "siar"
    prior = [y for y in out["years"] if y["year"] < 2026]
    assert prior, "expected RIA proxy years"
    assert all(y["source"] == "ria_proxy" for y in prior)
    assert out["comparisons"], "expected comparisons vs prior years"
    assert out["headline_es"]
    assert out["coverage"]["siar_years"] == [2026]
    assert 2022 in out["coverage"]["ria_proxy_years"]
    assert out["regional"] and out["by_province"]


if __name__ == "__main__":
    tests = [
        test_safe_through_caps_to_campaign_end,
        test_verdict_bands,
        test_plain_language,
        test_accumulate_sums_hm3,
        test_build_campaign_compare_mixed_sources,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"OK  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    if failed:
        raise SystemExit(1)
    print(f"All {len(tests)} tests passed.")
