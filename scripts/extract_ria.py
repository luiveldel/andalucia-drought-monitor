"""Ingesta diaria de datos agroclimáticos desde la API REST de la RIA (IFAPA)."""

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
)

logger = logging.getLogger(__name__)

RIA_API_BASE = "https://www.juntadeandalucia.es/agriculturaypesca/ifapa/riaws"
ESTACIONES_URL = f"{RIA_API_BASE}/estaciones"
RAW_TABLE = "raw.raw_ria_clima_diario"
REQUEST_TIMEOUT = 60


def fetch_stations() -> list[dict[str, Any]]:
    """Descarga catálogo de estaciones agroclimáticas."""
    response = requests.get(
        ESTACIONES_URL, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    stations = unwrap_api_payload(response.json())
    if not isinstance(stations, list):
        raise ValueError("Respuesta inesperada del catálogo de estaciones RIA")
    return stations


def fetch_station_day(
    provincia_id: int, codigo_estacion: str, partition_date: str
) -> list[dict[str, Any]]:
    """Descarga datos diarios de una estación para una fecha."""
    url = (
        f"{RIA_API_BASE}/datosdiarios/"
        f"{provincia_id}/{codigo_estacion}/{partition_date}/{partition_date}/true"
    )
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    if response.status_code in {404, 500, 502, 503}:
        logger.debug(
            "Sin datos RIA para %s/%s (%s): HTTP %s",
            provincia_id,
            codigo_estacion,
            partition_date,
            response.status_code,
        )
        return []
    response.raise_for_status()
    records = unwrap_api_payload(response.json())
    if records is None:
        return []
    if isinstance(records, dict):
        return [records]
    return records


def fetch_data(partition_date: str) -> list[dict[str, Any]]:
    """Descarga datos diarios de todas las estaciones activas para una fecha."""
    stations = fetch_stations()
    records: list[dict[str, Any]] = []

    for station in stations:
        if not station.get("activa", True):
            continue

        provincia = station.get("provincia") or {}
        provincia_id = provincia.get("id")
        codigo_estacion = station.get("codigoEstacion")
        if provincia_id is None or not codigo_estacion:
            continue

        day_rows = fetch_station_day(provincia_id, codigo_estacion, partition_date)
        for row in day_rows:
            records.append(
                {
                    "provincia_id": provincia_id,
                    "provincia_nombre": provincia.get("nombre"),
                    "codigo_estacion": codigo_estacion,
                    "nombre_estacion": station.get("nombre"),
                    **row,
                }
            )

    return records


def process_with_polars(raw_data: list[dict[str, Any]], partition_date: str) -> pl.DataFrame:
    """Materializa registros RIA en DataFrame Polars sin transformaciones de negocio."""
    if not raw_data:
        return pl.DataFrame()

    df = pl.DataFrame(raw_data)
    if "fecha" not in df.columns:
        df = df.with_columns(pl.lit(partition_date).alias("fecha"))

    return df.with_columns(pl.lit(datetime.now(timezone.utc)).alias("_loaded_at"))


def load_to_postgres(df: pl.DataFrame, partition_date: str) -> int:
    """Carga idempotente en raw.raw_ria_clima_diario para la fecha dada."""
    if df.is_empty():
        logger.warning("Sin filas para cargar en %s (%s)", RAW_TABLE, partition_date)
        return 0

    engine = get_engine_with_schema("raw")
    # Schema ensured by helper

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {RAW_TABLE} (
            fecha DATE NOT NULL,
            provincia_id INTEGER,
            provincia_nombre TEXT,
            codigo_estacion TEXT NOT NULL,
            nombre_estacion TEXT,
            temp_media DOUBLE PRECISION,
            temp_max DOUBLE PRECISION,
            temp_min DOUBLE PRECISION,
            humedad_media DOUBLE PRECISION,
            humedad_max DOUBLE PRECISION,
            humedad_min DOUBLE PRECISION,
            precipitacion DOUBLE PRECISION,
            radiacion DOUBLE PRECISION,
            vel_viento DOUBLE PRECISION,
            vel_viento_max DOUBLE PRECISION,
            dir_viento DOUBLE PRECISION,
            dir_viento_vel_max DOUBLE PRECISION,
            et0 DOUBLE PRECISION,
            bateria DOUBLE PRECISION,
            fecha_ult_mod TEXT,
            _loaded_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (fecha, provincia_id, codigo_estacion)
        )
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))

    column_map = {
        "tempMedia": "temp_media",
        "tempMax": "temp_max",
        "tempMin": "temp_min",
        "humedadMedia": "humedad_media",
        "humedadMax": "humedad_max",
        "humedadMin": "humedad_min",
        "velViento": "vel_viento",
        "velVientoMax": "vel_viento_max",
        "dirViento": "dir_viento",
        "dirVientoVelMax": "dir_viento_vel_max",
        "fechaUtlMod": "fecha_ult_mod",
    }
    load_df = df.rename({k: v for k, v in column_map.items() if k in df.columns})

    keep_cols = [
        "fecha",
        "provincia_id",
        "provincia_nombre",
        "codigo_estacion",
        "nombre_estacion",
        "temp_media",
        "temp_max",
        "temp_min",
        "humedad_media",
        "humedad_max",
        "humedad_min",
        "precipitacion",
        "radiacion",
        "vel_viento",
        "vel_viento_max",
        "dir_viento",
        "dir_viento_vel_max",
        "et0",
        "bateria",
        "fecha_ult_mod",
        "_loaded_at",
    ]
    existing_cols = [col for col in keep_cols if col in load_df.columns]
    load_df = load_df.select(existing_cols)

    delete_partition_for_date(engine, RAW_TABLE, "fecha", partition_date)
    write_polars_to_table(engine, load_df, "raw", "raw_ria_clima_diario")

    logger.info("Cargadas %s filas en %s para %s", load_df.height, RAW_TABLE, partition_date)
    return load_df.height


def run(partition_date: str) -> int:
    raw = fetch_data(partition_date)
    df = process_with_polars(raw, partition_date)
    return load_to_postgres(df, partition_date)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingesta diaria de datos RIA")
    parser.add_argument("--ds", required=True, help="Fecha de partición YYYY-MM-DD")
    args = parser.parse_args()
    run(args.ds)


if __name__ == "__main__":
    main()
