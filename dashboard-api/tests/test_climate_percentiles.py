"""Unit tests for multi-year ET0/demand percentiles (no DB / no pytest)."""

from __future__ import annotations

import sys
import types
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

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

from app.climate_percentiles import (  # noqa: E402
    MIN_YEARS_OK,
    _plain_en,
    _plain_es,
    empirical_percentiles,
    percentile_rank,
    build_climate_percentiles,
)


def test_empirical_percentiles_and_rank():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    pct = empirical_percentiles(vals)
    assert pct["p50"] == 3.0
    assert pct["p10"] is not None and pct["p90"] is not None
    # 5.0 is max among priors → high rank
    assert percentile_rank(5.0, vals) == 90.0
    assert percentile_rank(1.0, vals) == 10.0
    assert percentile_rank(3.0, [1.0, 2.0, 3.0]) is not None
    assert MIN_YEARS_OK >= 3


def test_plain_language_mentions_percentile():
    es = _plain_es(
        metric_label="ET0",
        rank=85.0,
        current=6.2,
        mean_v=4.5,
        unit="mm",
        n_years=4,
        context="mismo DOY 20/09",
    )
    assert "percentil 85" in es
    assert "más extremo" in es
    en = _plain_en(
        metric_label="ET0",
        rank=85.0,
        current=6.2,
        mean_v=4.5,
        unit="mm",
        n_years=4,
        context="same DOY 20/09",
    )
    assert "percentile 85" in en


def test_thin_history_still_compares_to_mean():
    es = _plain_es(
        metric_label="ET0",
        rank=None,
        current=5.0,
        mean_v=4.0,
        unit="mm",
        n_years=1,
        context="mismo DOY",
    )
    assert "media" in es.lower() or "Media" in es or "frente a media" in es
    assert "corto" in es.lower() or "orientativa" in es


def _fake_rows(conn, sql, **params):
    sql_l = " ".join(sql.lower().split())
    if "greatest(" in sql_l:
        return [{"d": "2026-09-20"}]
    if "min(fecha)" in sql_l and "raw_siar" in sql_l:
        return [{"mn": "2026-06-01", "mx": "2026-09-20"}]
    if "min(fecha)" in sql_l and "raw_ria" in sql_l:
        return [{"mn": "2024-01-01", "mx": "2026-09-19"}]
    if "extract(year from fecha)" in sql_l and "raw_siar" in sql_l:
        return [{"y": 2026}]
    if "extract(year from fecha)" in sql_l and "raw_ria" in sql_l:
        return [{"y": 2024}, {"y": 2025}, {"y": 2026}]
    if "from raw.raw_siar_clima_diario" in sql_l and "group by fecha" in sql_l:
        start = str(params.get("start", "2026-01-01"))
        year = int(start[:4])
        if year != 2026:
            return []
        rows = []
        # Apr–Sep daily + focus on 09-20
        for month, days_in in ((4, 30), (5, 31), (6, 30), (7, 31), (8, 31), (9, 20)):
            for d in range(1, days_in + 1):
                for prov in ("Sevilla", "Jaén"):
                    rows.append(
                        {
                            "d": f"{year}-{month:02d}-{d:02d}",
                            "province_name": prov,
                            "station_count": 3,
                            "et0_mm": 6.0,
                            "pe_mm": 0.0,
                            "precip_mm": 0.0,
                        }
                    )
        return rows
    if "from raw.raw_ria_clima_diario" in sql_l and "group by fecha" in sql_l:
        start = str(params.get("start", "2024-01-01"))
        year = int(start[:4])
        et0 = {2024: 4.0, 2025: 5.0, 2026: 5.5}.get(year, 4.0)
        rows = []
        for month, days_in in ((4, 30), (5, 31), (6, 30), (7, 31), (8, 31), (9, 20)):
            for d in range(1, days_in + 1):
                for prov in ("Sevilla", "Jaén"):
                    rows.append(
                        {
                            "d": f"{year}-{month:02d}-{d:02d}",
                            "province_name": prov,
                            "station_count": 2,
                            "et0_mm": et0,
                            "pe_mm": 0.5,
                            "precip_mm": 0.5,
                        }
                    )
        return rows
    return []


def test_build_climate_percentiles_mixed_sources():
    conn = MagicMock()
    with patch("app.climate_percentiles._rows", side_effect=_fake_rows):
        out = build_climate_percentiles(conn, as_of=date(2026, 9, 20))
    assert out["available"] is True
    assert out["current_year"] == 2026
    assert out["regional"] is not None
    et0 = out["regional"]["same_doy"]["et0"]
    assert et0["current"] is not None
    # 2026 SiAR + 2024/2025 RIA priors
    assert et0["n_years"] >= 2
    assert et0["percentile_rank"] is not None
    assert "percentil" in (out["headline_es"] or "").lower() or "media" in (
        out["headline_es"] or ""
    ).lower()
    cov = out["coverage"]
    assert 2026 in (cov.get("siar_years") or [])
    assert any(y in (cov.get("ria_proxy_years") or []) for y in (2024, 2025))
    # campaign cumulative present
    assert out["regional"]["campaign_to_date"]["net_demand_mm_cum"]["current"] is not None
    assert out["by_province"], "expected provincial rows"
    # Must not invent years without data
    sample_years = {s["year"] for s in et0["samples"]}
    assert sample_years <= {2024, 2025, 2026}


def test_empty_when_no_dates():
    conn = MagicMock()

    def empty_rows(conn, sql, **params):
        sql_l = " ".join(sql.lower().split())
        if "greatest(" in sql_l:
            return [{"d": "1900-01-01"}]
        return []

    with patch("app.climate_percentiles._rows", side_effect=empty_rows):
        out = build_climate_percentiles(conn)
    assert out["available"] is False


if __name__ == "__main__":
    test_empirical_percentiles_and_rank()
    test_plain_language_mentions_percentile()
    test_thin_history_still_compares_to_mean()
    test_build_climate_percentiles_mixed_sources()
    test_empty_when_no_dates()
    print("OK all climate_percentiles tests passed")
