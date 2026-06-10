"""Full-refresh ingest of the REDIAM reservoir catalog (metadata)."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any

import polars as pl
from sqlalchemy import text

from extract_embalses import fetch_catalog
from common import get_engine_with_schema, load_settings, write_polars_to_table

logger = logging.getLogger(__name__)

settings = load_settings()

RAW_TABLE = "raw_embalses_catalog"


def fetch_data() -> list[dict[str, Any]]:
    """Download the full reservoir catalog from REDIAM."""
    return fetch_catalog()


def process_with_polars(raw_data: list[dict[str, Any]]) -> pl.DataFrame:
    """Persist catalog rows with source field names (bronze layer)."""
    if not raw_data:
        return pl.DataFrame()

    return pl.DataFrame(raw_data).with_columns(
        pl.lit(datetime.now(timezone.utc)).alias("_loaded_at")
    )


def load_to_postgres(df: pl.DataFrame) -> int:
    """Replace the full catalog snapshot in raw.raw_embalses_catalog."""
    if df.is_empty():
        logger.warning("No catalog rows to load into %s", RAW_TABLE)
        return 0

    engine = get_engine_with_schema(settings['schema'])
    # Schema ensured by helper

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {settings['schema']}.{RAW_TABLE} (
            fid INTEGER,
            cod_est TEXT NOT NULL,
            tipo TEXT,
            nombre TEXT,
            provincia TEXT,
            sistema TEXT,
            dist_dem TEXT,
            nombre_rio TEXT,
            geom TEXT,
            nom_pres TEXT,
            _loaded_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (cod_est)
        )
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))
        conn.execute(text(f"TRUNCATE TABLE {settings['schema']}.{RAW_TABLE}"))

    write_polars_to_table(engine, df, settings['schema'], RAW_TABLE)

    logger.info("Loaded %s catalog rows into %s", df.height, RAW_TABLE)
    return df.height


def run() -> int:
    raw = fetch_data()
    df = process_with_polars(raw)
    return load_to_postgres(df)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()
