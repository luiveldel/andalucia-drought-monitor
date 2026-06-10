"""Utilidades compartidas para scripts de ingesta."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

import polars as pl
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DEFAULT_HEADERS = {
    "User-Agent": "andalucia-drought-monitor/1.0 (data-engineering; open-data)",
    "Accept": "application/json",
}


def get_dwh_connection_string() -> str:
    host = os.environ.get("POSTGRES_DWH_HOST", "localhost")
    port = os.environ.get("POSTGRES_DWH_PORT", "5432")
    database = os.environ.get("POSTGRES_DWH_DB", "agro_sequia")
    user = os.environ.get("POSTGRES_DWH_USER", "dwh_user")
    password = os.environ.get("POSTGRES_DWH_PASSWORD", "dwh_password")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def get_engine() -> Engine:
    """Create a SQLAlchemy engine using the DWH connection string."""
    return create_engine(get_dwh_connection_string())

def get_engine_with_schema(schema: str = "raw") -> Engine:
    """Return an engine and ensure the given schema exists.

    This helper reduces repetition by creating the engine and invoking
    ``ensure_schema`` in a single call.
    """
    engine = get_engine()
    ensure_schema(engine, schema)
    return engine


def unwrap_api_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def ensure_schema(engine: Engine, schema: str = "raw") -> None:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))


def delete_partition_for_date(
    engine: Engine, table: str, date_column: str, partition_date: str
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(f"DELETE FROM {table} WHERE {date_column} = :partition_date"),
            {"partition_date": partition_date},
        )


def write_polars_to_table(
    engine: Engine, df: pl.DataFrame, schema: str, table: str
) -> None:
    if df.is_empty():
        return

    rows = df.to_dicts()
    columns = list(df.columns)
    qualified_table = f"{schema}.{table}"
    placeholders = ", ".join(f":{column}" for column in columns)
    column_list = ", ".join(columns)
    insert_sql = text(
        f"INSERT INTO {qualified_table} ({column_list}) VALUES ({placeholders})"
    )
    with engine.begin() as conn:
        conn.execute(insert_sql, rows)

def load_settings() -> dict[str, Any]:
    with (Path(__file__).parent / "config.yml").open() as f:
        return yaml.safe_load(f.read())
