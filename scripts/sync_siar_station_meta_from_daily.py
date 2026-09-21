"""Build raw.raw_siar_estaciones from daily rows that already have coords.

Does NOT call the SiAR API — bootstrap the station↔embalse map when a day
was ingested with station meta (latitud_raw/longitud_raw), or after quota
recovers and one daily run with meta lands.
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from common import get_engine_with_schema

logger = logging.getLogger(__name__)

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS raw.raw_siar_estaciones (
    ccaa_codigo TEXT NOT NULL,
    codigo_estacion TEXT NOT NULL,
    nombre_estacion TEXT,
    provincia_nombre TEXT,
    latitud_raw TEXT,
    longitud_raw TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ccaa_codigo, codigo_estacion)
)
"""

UPSERT_SQL = """
INSERT INTO raw.raw_siar_estaciones (
    ccaa_codigo, codigo_estacion, nombre_estacion, provincia_nombre,
    latitud_raw, longitud_raw, _loaded_at
)
SELECT DISTINCT ON (d.ccaa_codigo, d.codigo_estacion)
    d.ccaa_codigo,
    TRIM(d.codigo_estacion),
    NULLIF(TRIM(d.nombre_estacion), ''),
    NULLIF(TRIM(d.provincia_nombre), ''),
    NULLIF(TRIM(d.latitud_raw), ''),
    NULLIF(TRIM(d.longitud_raw), ''),
    NOW()
FROM raw.raw_siar_clima_diario d
WHERE d.ccaa_codigo = 'AND'
  AND TRIM(COALESCE(d.codigo_estacion, '')) <> ''
  AND NULLIF(TRIM(d.latitud_raw), '') IS NOT NULL
  AND NULLIF(TRIM(d.longitud_raw), '') IS NOT NULL
ORDER BY d.ccaa_codigo, d.codigo_estacion, d.fecha DESC NULLS LAST
ON CONFLICT (ccaa_codigo, codigo_estacion) DO UPDATE SET
    nombre_estacion = EXCLUDED.nombre_estacion,
    provincia_nombre = EXCLUDED.provincia_nombre,
    latitud_raw = EXCLUDED.latitud_raw,
    longitud_raw = EXCLUDED.longitud_raw,
    _loaded_at = NOW()
"""


def run() -> int:
    engine = get_engine_with_schema("raw")
    with engine.begin() as conn:
        conn.execute(text(CREATE_SQL))
        conn.execute(text(UPSERT_SQL))
        n = conn.execute(
            text("SELECT COUNT(*) FROM raw.raw_siar_estaciones WHERE ccaa_codigo='AND'")
        ).scalar()
    logger.info("raw_siar_estaciones AND rows=%s", n)
    return int(n or 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(run())
