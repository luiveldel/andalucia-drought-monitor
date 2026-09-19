"""Ingesta diaria de datos agroclimáticos desde la Web API SiAR (MAPA).

Complementa RIA/IFAPA: red nacional de estaciones de riego del Ministerio.
Documentación: Manual Técnico Web API SiAR (servicio.mapa.gob.es/siarapi).
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from typing import Any

import polars as pl
import requests
from sqlalchemy import text

from common import (
    DEFAULT_HEADERS,
    delete_partition_for_date,
    get_engine_with_schema,
    write_polars_to_table,
)

logger = logging.getLogger(__name__)

SIAR_API_BASE = os.environ.get(
    "SIAR_API_BASE", "https://servicio.mapa.gob.es/siarapi/API/V1"
).rstrip("/")
RAW_TABLE = "raw.raw_siar_clima_diario"
REQUEST_TIMEOUT = 120
DEFAULT_CCAA = "AND"

# Código de estación SiAR → provincia (Andalucía).
# La mayoría usa prefijo de 2 letras (AL, SE…); Huelva/Jaén usan H## / J##.
STATION_PREFIX_PROVINCE: dict[str, str] = {
    "AL": "Almería",
    "CA": "Cádiz",
    "CO": "Córdoba",
    "GR": "Granada",
    "HU": "Huelva",
    "JA": "Jaén",
    "MA": "Málaga",
    "SE": "Sevilla",
}


def province_from_station_code(station_code: str) -> str | None:
    code = (station_code or "").strip().upper()
    if not code:
        return None
    if code[:2] in STATION_PREFIX_PROVINCE:
        return STATION_PREFIX_PROVINCE[code[:2]]
    if code[0] == "H" and code[1:].isdigit():
        return "Huelva"
    if code[0] == "J" and code[1:].isdigit():
        return "Jaén"
    return None


def _api_token() -> str:
    token = (
        os.environ.get("SIAR_API_KEY")
        or os.environ.get("API_KEY_SIAR_MAPA")
        or ""
    ).strip()
    if not token:
        raise RuntimeError(
            "Falta SIAR_API_KEY en el entorno (.env). "
            "Alta en https://servicio.mapa.gob.es/siarweb/"
        )
    return token


def _get_json(path: str, params: dict[str, Any]) -> dict[str, Any]:
    query = {**params, "token": _api_token()}
    url = f"{SIAR_API_BASE}{path}"
    response = requests.get(
        url, params=query, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT
    )
    if response.status_code == 403:
        raise RuntimeError(
            "SiAR API 403 (límite de accesos o token inválido). "
            f"Mensaje: {response.text[:300]}"
        )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"Respuesta inesperada de SiAR {path}: {type(payload)}")
    return payload


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("datos")
    if data is None:
        data = payload.get("Datos")
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def fetch_stations(ccaa: str = DEFAULT_CCAA) -> list[dict[str, Any]]:
    """Catálogo de estaciones; filtra por CCAA cuando el campo existe."""
    payload = _get_json("/Info/ESTACIONES", {})
    rows = _rows(payload)
    if not rows:
        return []

    filtered: list[dict[str, Any]] = []
    for row in rows:
        code_ccaa = (
            row.get("Codigo_CCAA")
            or row.get("Codigo_CCCAA")
            or row.get("CodigoCCAA")
        )
        if code_ccaa:
            if str(code_ccaa).upper() == ccaa.upper():
                filtered.append(row)
            continue
        codigo = str(row.get("Codigo") or "")
        if province_from_station_code(codigo):
            filtered.append(row)
    return filtered or rows


def fetch_daily_ccaa(
    partition_date: str, ccaa: str = DEFAULT_CCAA, calculated: bool = True
) -> list[dict[str, Any]]:
    """Datos diarios de todas las estaciones de una CCAA para una fecha."""
    payload = _get_json(
        f"/Datos/Diarios/CCAA",
        {
            "Id": ccaa,
            "FechaInicial": partition_date,
            "FechaFinal": partition_date,
            "DatosCalculados": "true" if calculated else "false",
        },
    )
    msg = payload.get("MensajeRespuesta") or payload.get("mensajeRespuesta")
    if msg:
        logger.info("SiAR MensajeRespuesta: %s", msg)
    return _rows(payload)


def _province_name(station_code: str, stations_by_code: dict[str, dict[str, Any]]) -> str | None:
    meta = stations_by_code.get(station_code) or {}
    for key in ("Provincia", "provincia", "NombreProvincia"):
        if meta.get(key):
            return str(meta[key])
    return province_from_station_code(station_code)


def _station_name(station_code: str, stations_by_code: dict[str, dict[str, Any]]) -> str | None:
    meta = stations_by_code.get(station_code) or {}
    for key in ("Estacion", "Nombre", "nombre", "Termino"):
        # Info catalog uses Estacion as name; daily rows use Estacion as code.
        if key == "Estacion" and meta.get(key) and meta.get(key) != station_code:
            return str(meta[key])
        if key != "Estacion" and meta.get(key):
            return str(meta[key])
    if meta.get("Estacion") and meta.get("Codigo") == station_code:
        return str(meta["Estacion"])
    return meta.get("Termino")


def fetch_data(
    partition_date: str,
    ccaa: str = DEFAULT_CCAA,
    *,
    with_station_meta: bool = False,
) -> list[dict[str, Any]]:
    """Une lecturas diarias SiAR con metadatos de estación.

    ``with_station_meta`` llama a /Info/ESTACIONES (consume cuota SiAR).
    Por defecto se usa solo el prefijo del código (AL/CA/…) para la provincia.
    """
    stations_by_code: dict[str, dict[str, Any]] = {}
    if with_station_meta:
        try:
            stations = fetch_stations(ccaa)
            for st in stations:
                code = str(st.get("Codigo") or st.get("codigo") or "").strip()
                if code:
                    stations_by_code[code] = st
        except Exception as exc:  # noqa: BLE001 — meta is optional
            logger.warning("Catálogo SiAR no disponible (%s); sigo sin meta", exc)

    day_rows = fetch_daily_ccaa(partition_date, ccaa=ccaa)
    records: list[dict[str, Any]] = []
    for row in day_rows:
        station_code = str(row.get("Estacion") or "").strip()
        if not station_code:
            continue
        meta = stations_by_code.get(station_code, {})
        fecha = row.get("Fecha") or partition_date
        if isinstance(fecha, str) and "T" in fecha:
            fecha = fecha.split("T", 1)[0]

        records.append(
            {
                "fecha": fecha,
                "ccaa_codigo": ccaa,
                "codigo_estacion": station_code,
                "nombre_estacion": _station_name(station_code, stations_by_code),
                "provincia_nombre": _province_name(station_code, stations_by_code),
                "termino": meta.get("Termino"),
                "altitud": meta.get("Altitud"),
                "latitud_raw": meta.get("Latitud"),
                "longitud_raw": meta.get("Longitud"),
                "temp_media": row.get("TempMedia"),
                "temp_max": row.get("TempMax"),
                "temp_min": row.get("TempMin"),
                "humedad_media": row.get("HumedadMedia"),
                "humedad_max": row.get("HumedadMax"),
                "humedad_min": row.get("humedadMin") or row.get("HumedadMin"),
                "vel_viento": row.get("VelViento"),
                "dir_viento": row.get("DirViento"),
                "vel_viento_max": row.get("VelVientoMax"),
                "dir_viento_vel_max": row.get("DirVientoVelMax"),
                "radiacion": row.get("Radiacion"),
                "precipitacion": row.get("Precipitacion"),
                "et0": row.get("EtPMon") or row.get("ET0") or row.get("Et0"),
                "precip_efectiva": row.get("PePMon") or row.get("PrecipitacionEfectiva"),
                "temp_suelo_1": row.get("TempSuelo1"),
                "temp_suelo_2": row.get("TempSuelo2"),
                "hora_temp_max": row.get("HorMinTempMax"),
                "hora_temp_min": row.get("HorMinTempMin"),
            }
        )
    return records


def process_with_polars(raw_data: list[dict[str, Any]], partition_date: str) -> pl.DataFrame:
    if not raw_data:
        return pl.DataFrame()
    df = pl.DataFrame(raw_data)
    if "fecha" not in df.columns:
        df = df.with_columns(pl.lit(partition_date).alias("fecha"))
    return df.with_columns(pl.lit(datetime.now(timezone.utc)).alias("_loaded_at"))


def load_to_postgres(df: pl.DataFrame, partition_date: str) -> int:
    if df.is_empty():
        logger.warning("Sin filas para cargar en %s (%s)", RAW_TABLE, partition_date)
        return 0

    engine = get_engine_with_schema("raw")
    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {RAW_TABLE} (
            fecha DATE NOT NULL,
            ccaa_codigo TEXT NOT NULL,
            codigo_estacion TEXT NOT NULL,
            nombre_estacion TEXT,
            provincia_nombre TEXT,
            termino TEXT,
            altitud DOUBLE PRECISION,
            latitud_raw TEXT,
            longitud_raw TEXT,
            temp_media DOUBLE PRECISION,
            temp_max DOUBLE PRECISION,
            temp_min DOUBLE PRECISION,
            humedad_media DOUBLE PRECISION,
            humedad_max DOUBLE PRECISION,
            humedad_min DOUBLE PRECISION,
            vel_viento DOUBLE PRECISION,
            dir_viento DOUBLE PRECISION,
            vel_viento_max DOUBLE PRECISION,
            dir_viento_vel_max DOUBLE PRECISION,
            radiacion DOUBLE PRECISION,
            precipitacion DOUBLE PRECISION,
            et0 DOUBLE PRECISION,
            precip_efectiva DOUBLE PRECISION,
            temp_suelo_1 DOUBLE PRECISION,
            temp_suelo_2 DOUBLE PRECISION,
            hora_temp_max INTEGER,
            hora_temp_min INTEGER,
            _loaded_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (fecha, ccaa_codigo, codigo_estacion)
        )
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))

    keep_cols = [
        "fecha",
        "ccaa_codigo",
        "codigo_estacion",
        "nombre_estacion",
        "provincia_nombre",
        "termino",
        "altitud",
        "latitud_raw",
        "longitud_raw",
        "temp_media",
        "temp_max",
        "temp_min",
        "humedad_media",
        "humedad_max",
        "humedad_min",
        "vel_viento",
        "dir_viento",
        "vel_viento_max",
        "dir_viento_vel_max",
        "radiacion",
        "precipitacion",
        "et0",
        "precip_efectiva",
        "temp_suelo_1",
        "temp_suelo_2",
        "hora_temp_max",
        "hora_temp_min",
        "_loaded_at",
    ]
    existing = [c for c in keep_cols if c in df.columns]
    load_df = df.select(existing)

    delete_partition_for_date(engine, RAW_TABLE, "fecha", partition_date)
    write_polars_to_table(engine, load_df, "raw", "raw_siar_clima_diario")
    logger.info("Cargadas %s filas en %s para %s", load_df.height, RAW_TABLE, partition_date)
    return load_df.height


def run(
    partition_date: str,
    ccaa: str = DEFAULT_CCAA,
    *,
    with_station_meta: bool = False,
) -> int:
    raw = fetch_data(
        partition_date, ccaa=ccaa, with_station_meta=with_station_meta
    )
    df = process_with_polars(raw, partition_date)
    return load_to_postgres(df, partition_date)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingesta diaria de datos SiAR (MAPA)")
    parser.add_argument("--ds", required=True, help="Fecha de partición YYYY-MM-DD")
    parser.add_argument("--ccaa", default=DEFAULT_CCAA, help="Código CCAA SiAR (AND)")
    parser.add_argument(
        "--with-station-meta",
        action="store_true",
        help="También llama a /Info/ESTACIONES (consume cuota por minuto)",
    )
    args = parser.parse_args()
    run(args.ds, ccaa=args.ccaa, with_station_meta=args.with_station_meta)


if __name__ == "__main__":
    main()
