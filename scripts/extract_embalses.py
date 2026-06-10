"""Ingesta diaria de embalses desde REDIAM (Embalses al día)."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any

import polars as pl
import requests
from sqlalchemy import text

from common import (
    DEFAULT_HEADERS,
    delete_partition_for_date,
    get_engine_with_schema,
    unwrap_api_payload,
    write_polars_to_table,
    load_settings,
)

logger = logging.getLogger(__name__)

settings = load_settings()

EMBALSES_API_BASE = "https://portalrediam.cica.es/embalses/api/json"
EMBALSES_CATALOG_URL = f"{EMBALSES_API_BASE}/embalses"
RAW_TABLE = "raw_embalses_diarios"
REQUEST_TIMEOUT = 60


def fetch_data(partition_date: str) -> dict[str, Any]:
    """Descarga snapshot diario de reservas para una fecha (YYYY-MM-DD)."""
    url = f"{EMBALSES_API_BASE}/andalucia/{partition_date}"
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if payload.get("fecha") != partition_date:
        logger.warning(
            "API devolvió fecha %s distinta a solicitada %s",
            payload.get("fecha"),
            partition_date,
        )
    return payload


def fetch_catalog() -> list[dict[str, Any]]:
    """Descarga catálogo de embalses (metadatos)."""
    response = requests.get(
        EMBALSES_CATALOG_URL, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return unwrap_api_payload(response.json())


def process_with_polars(raw_data: dict[str, Any], partition_date: str) -> pl.DataFrame:
    """Convierte JSON ancho de REDIAM a filas (bronze, sin limpieza de negocio)."""
    fecha = str(raw_data.get("fecha", partition_date))
    rows: list[dict[str, Any]] = []

    for key, value in raw_data.items():
        if key == "fecha" or not key.endswith("_res"):
            continue
        cod_est = key.removesuffix("_res")
        rows.append(
            {
                "fecha": fecha,
                "cod_est": cod_est,
                "reserva_hm3": raw_data.get(f"{cod_est}_res"),
                "capacidad_hm3": raw_data.get(f"{cod_est}_cap"),
                "porcentaje_llenado": raw_data.get(f"{cod_est}_por"),
            }
        )

    return pl.DataFrame(rows).with_columns(
        pl.lit(datetime.now(timezone.utc)).alias("_loaded_at")
    )


def load_to_postgres(df: pl.DataFrame, partition_date: str) -> int:
    """Carga idempotente en raw.raw_embalses_diarios para la fecha dada."""
    if df.is_empty():
        logger.warning("Sin filas para cargar en %s (%s)", RAW_TABLE, partition_date)
        return 0

    engine = get_engine_with_schema(settings['schema'])

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {settings['schema']}.{RAW_TABLE} (
            fecha DATE NOT NULL,
            cod_est TEXT NOT NULL,
            reserva_hm3 DOUBLE PRECISION,
            capacidad_hm3 DOUBLE PRECISION,
            porcentaje_llenado DOUBLE PRECISION,
            _loaded_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (fecha, cod_est)
        )
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))

    delete_partition_for_date(engine, f"{settings['schema']}.{RAW_TABLE}", "fecha", partition_date)
    write_polars_to_table(engine, df, settings['schema'], RAW_TABLE)

    logger.info("Cargadas %s filas en %s para %s", df.height, RAW_TABLE, partition_date)
    return df.height


def run(partition_date: str) -> int:
    raw = fetch_data(partition_date)
    df = process_with_polars(raw, partition_date)
    return load_to_postgres(df, partition_date)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingesta diaria de embalses REDIAM")
    parser.add_argument("--ds", required=True, help="Fecha de partición YYYY-MM-DD")
    args = parser.parse_args()
    run(args.ds)


if __name__ == "__main__":
    main()
