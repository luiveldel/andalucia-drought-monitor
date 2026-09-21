"""Ingesta horaria / semihoraria SiAR (MAPA) → raw.raw_siar_clima_horario.

Endpoint documentado por clientes públicos (p. ej. La Rioja):
  GET {SIAR_API_BASE}/Datos/Horarios/CCAA?Id=AND&FechaInicial=…&FechaFinal=…&token=…

La respuesta suele traer HoraMin en formato HHMM (30, 100, 130…) = semihorario.
Requiere SIAR_API_KEY. Sin clave, este script falla de forma explícita; el
dashboard usa Open-Meteo como proxy etiquetado hasta que la tabla exista.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import polars as pl
import requests
from sqlalchemy import text

from common import (
    DEFAULT_HEADERS,
    get_engine_with_schema,
    write_polars_to_table,
)
from extract_siar import (
    DEFAULT_CCAA,
    SIAR_API_BASE,
    REQUEST_TIMEOUT,
    _api_token,
    _get_json,
    _rows,
    province_from_station_code,
)

logger = logging.getLogger(__name__)

RAW_TABLE = "raw.raw_siar_clima_horario"
RAW_TABLE_NAME = "raw_siar_clima_horario"


def fetch_hourly_ccaa(
    fecha_inicial: str,
    fecha_final: str,
    ccaa: str = DEFAULT_CCAA,
) -> list[dict[str, Any]]:
    """Datos horarios/semihorarios de todas las estaciones de una CCAA."""
    payload = _get_json(
        "/Datos/Horarios/CCAA",
        {
            "Id": ccaa,
            "FechaInicial": fecha_inicial,
            "FechaFinal": fecha_final,
        },
    )
    msg = payload.get("MensajeRespuesta") or payload.get("mensajeRespuesta")
    if msg:
        logger.info("SiAR Horarios MensajeRespuesta: %s", msg)
    return _rows(payload)


def _normalize_row(row: dict[str, Any], ccaa: str) -> dict[str, Any] | None:
    station_code = str(row.get("Estacion") or row.get("estacion") or "").strip()
    if not station_code:
        return None
    fecha = row.get("Fecha") or row.get("fecha")
    if isinstance(fecha, str) and "T" in fecha:
        fecha = fecha.split("T", 1)[0]
    if not fecha:
        return None
    hora_min = row.get("HoraMin")
    if hora_min is None:
        hora_min = row.get("Hora") or row.get("hora_min")
    try:
        hora_min_i = int(hora_min) if hora_min is not None else None
    except (TypeError, ValueError):
        hora_min_i = None
    if hora_min_i is None:
        return None

    return {
        "fecha": fecha,
        "hora_min": hora_min_i,
        "ccaa_codigo": ccaa,
        "codigo_estacion": station_code,
        "provincia_nombre": province_from_station_code(station_code),
        "temp_media": row.get("TempMedia") or row.get("tempMedia"),
        "humedad_media": row.get("HumedadMedia") or row.get("humedadMedia"),
        "vel_viento": row.get("VelViento"),
        "dir_viento": row.get("DirViento"),
        "radiacion": row.get("Radiacion"),
        "precipitacion": row.get("Precipitacion"),
        "et0": row.get("EtPMon") or row.get("ET0") or row.get("Et0"),
        "temp_suelo_1": row.get("TempSuelo1"),
        "temp_suelo_2": row.get("TempSuelo2"),
    }


def fetch_data(fecha_inicial: str, fecha_final: str, ccaa: str = DEFAULT_CCAA) -> list[dict[str, Any]]:
    raw = fetch_hourly_ccaa(fecha_inicial, fecha_final, ccaa=ccaa)
    out: list[dict[str, Any]] = []
    for row in raw:
        norm = _normalize_row(row, ccaa)
        if norm:
            out.append(norm)
    return out


def process_with_polars(raw_data: list[dict[str, Any]]) -> pl.DataFrame:
    if not raw_data:
        return pl.DataFrame()
    return pl.DataFrame(raw_data).with_columns(
        pl.lit(datetime.now(timezone.utc)).alias("_loaded_at")
    )


def load_to_postgres(
    df: pl.DataFrame,
    fecha_inicial: str,
    fecha_final: str,
    ccaa: str = DEFAULT_CCAA,
) -> int:
    if df.is_empty():
        logger.warning("Sin filas horarias SiAR (%s → %s)", fecha_inicial, fecha_final)
        return 0

    engine = get_engine_with_schema("raw")
    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {RAW_TABLE} (
            fecha DATE NOT NULL,
            hora_min INTEGER NOT NULL,
            ccaa_codigo TEXT NOT NULL,
            codigo_estacion TEXT NOT NULL,
            provincia_nombre TEXT,
            temp_media DOUBLE PRECISION,
            humedad_media DOUBLE PRECISION,
            vel_viento DOUBLE PRECISION,
            dir_viento DOUBLE PRECISION,
            radiacion DOUBLE PRECISION,
            precipitacion DOUBLE PRECISION,
            et0 DOUBLE PRECISION,
            temp_suelo_1 DOUBLE PRECISION,
            temp_suelo_2 DOUBLE PRECISION,
            _loaded_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (fecha, hora_min, ccaa_codigo, codigo_estacion)
        )
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))
        conn.execute(
            text(
                f"""
                DELETE FROM {RAW_TABLE}
                WHERE ccaa_codigo = :ccaa
                  AND fecha >= CAST(:fi AS date)
                  AND fecha <= CAST(:ff AS date)
                """
            ),
            {
                "ccaa": ccaa,
                "fi": fecha_inicial,
                "ff": fecha_final,
            },
        )

    keep = [
        "fecha",
        "hora_min",
        "ccaa_codigo",
        "codigo_estacion",
        "provincia_nombre",
        "temp_media",
        "humedad_media",
        "vel_viento",
        "dir_viento",
        "radiacion",
        "precipitacion",
        "et0",
        "temp_suelo_1",
        "temp_suelo_2",
        "_loaded_at",
    ]
    existing = [c for c in keep if c in df.columns]
    load_df = df.select(existing)
    write_polars_to_table(engine, load_df, "raw", RAW_TABLE_NAME)
    logger.info(
        "Cargadas %s filas en %s (%s → %s)",
        load_df.height,
        RAW_TABLE,
        fecha_inicial,
        fecha_final,
    )
    return load_df.height


def run(fecha_inicial: str, fecha_final: str | None = None, ccaa: str = DEFAULT_CCAA) -> int:
    fecha_final = fecha_final or fecha_inicial
    raw = fetch_data(fecha_inicial, fecha_final, ccaa=ccaa)
    df = process_with_polars(raw)
    return load_to_postgres(df, fecha_inicial, fecha_final, ccaa=ccaa)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingesta horaria SiAR (MAPA)")
    parser.add_argument("--ds", required=True, help="Fecha inicial YYYY-MM-DD")
    parser.add_argument("--de", default=None, help="Fecha final YYYY-MM-DD (default = --ds)")
    parser.add_argument("--ccaa", default=DEFAULT_CCAA, help="Código CCAA SiAR (AND)")
    args = parser.parse_args()
    run(args.ds, fecha_final=args.de, ccaa=args.ccaa)


if __name__ == "__main__":
    main()
