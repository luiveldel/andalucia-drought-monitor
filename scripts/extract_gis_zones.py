"""Full-refresh ingest of agricultural zone polygons (SIGPAC / open GIS) into PostGIS."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import geopandas as gpd
import requests
from sqlalchemy import text

from common import DEFAULT_HEADERS, get_dwh_connection_string, get_engine_with_schema, load_settings

logger = logging.getLogger(__name__)

settings = load_settings()

RAW_TABLE = "raw_gis_agricultural_zones"
DEFAULT_GIS_URL = os.environ.get(
    "GIS_AGRICULTURAL_ZONES_URL",
    "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/spain-provinces.geojson",
)
REQUEST_TIMEOUT = 300


def _resolve_local_path(file_path: Path) -> Path:
    """Return a path GeoPandas can read (handles zip archives)."""
    if file_path.suffix.lower() != ".zip":
        return file_path

    with zipfile.ZipFile(file_path) as archive:
        vector_extensions = {".geojson", ".json", ".gpkg", ".shp"}
        members = [
            name
            for name in archive.namelist()
            if Path(name).suffix.lower() in vector_extensions
        ]
        if not members:
            raise ValueError(f"No vector layer found inside zip: {file_path}")

        extract_dir = file_path.parent / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        archive.extract(members[0], path=extract_dir)
        return extract_dir / members[0]


def fetch_data(url: str) -> Path:
    """Download GIS file (GeoJSON, GeoPackage, Shapefile or zip) to a temp path."""
    logger.info("Downloading GIS data from %s", url)

    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower() or ".geojson"
    if suffix not in {".geojson", ".json", ".zip", ".gpkg", ".shp"}:
        suffix = ".geojson"

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = Path(temp_file.name)
    temp_file.close()

    with requests.get(
        url, headers=DEFAULT_HEADERS, stream=True, timeout=REQUEST_TIMEOUT
    ) as response:
        response.raise_for_status()
        with temp_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)

    logger.info("GIS file saved to %s", temp_path)
    return temp_path


def process_with_geopandas(file_path: Path) -> gpd.GeoDataFrame:
    """Read spatial file, normalize CRS to EPSG:4326 (WGS84)."""
    readable_path = _resolve_local_path(file_path)
    logger.info("Reading GIS layer from %s", readable_path)

    gdf = gpd.read_file(readable_path)
    if gdf.empty:
        raise ValueError(f"GIS layer is empty: {readable_path}")

    if gdf.crs is None:
        logger.warning("Source CRS missing; assuming EPSG:4326")
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        logger.info("Reprojecting from EPSG:%s to EPSG:4326", gdf.crs.to_epsg())
        gdf = gdf.to_crs(epsg=4326)

    invalid_mask = ~gdf.geometry.is_valid
    if invalid_mask.any():
        logger.warning("Fixing %s invalid geometries with buffer(0)", invalid_mask.sum())
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].buffer(0)

    gdf["_loaded_at"] = datetime.now(timezone.utc)
    return gdf


def load_to_postgres(gdf: gpd.GeoDataFrame) -> int:
    """Write GeoDataFrame to PostGIS without pandas.to_sql / to_postgis.

    Airflow's pandas 2.2 + SQLAlchemy 1.4 combo breaks both helpers
    ("geometry not a string" / "no attribute cursor").
    """
    engine = get_engine_with_schema(settings["schema"])
    schema = settings["schema"]
    full_table = f"{schema}.{RAW_TABLE}"

    df = gdf.drop(columns=[gdf.geometry.name]).copy()
    df["_geometry_wkt"] = gdf.geometry.to_wkt()
    df = df.where(df.notna(), None)

    col_defs: list[str] = []
    for col, dtype in df.dtypes.items():
        dtype_s = str(dtype)
        if col == "_geometry_wkt":
            col_defs.append(f'"{col}" text')
        elif dtype_s.startswith("datetime"):
            col_defs.append(f'"{col}" timestamptz')
        elif dtype_s.startswith("int"):
            col_defs.append(f'"{col}" bigint')
        elif dtype_s.startswith("float"):
            col_defs.append(f'"{col}" double precision')
        elif dtype_s == "bool":
            col_defs.append(f'"{col}" boolean')
        else:
            col_defs.append(f'"{col}" text')

    columns = list(df.columns)
    col_list = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    rows = df.to_dict(orient="records")

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text(f"DROP TABLE IF EXISTS {full_table} CASCADE"))
        conn.execute(text(f"CREATE TABLE {full_table} ({', '.join(col_defs)})"))
        if rows:
            conn.execute(
                text(f"INSERT INTO {full_table} ({col_list}) VALUES ({placeholders})"),
                rows,
            )
        conn.execute(
            text(
                f"ALTER TABLE {full_table} "
                f"ADD COLUMN geometry geometry(MultiPolygon, 4326)"
            )
        )
        conn.execute(
            text(
                f"UPDATE {full_table} SET geometry = "
                f"ST_Multi(ST_SetSRID(ST_GeomFromText(_geometry_wkt), 4326))"
            )
        )
        conn.execute(text(f"ALTER TABLE {full_table} DROP COLUMN _geometry_wkt"))
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS idx_{RAW_TABLE}_geom "
                f"ON {full_table} USING GIST (geometry)"
            )
        )

    return len(gdf)



def run(url: str | None = None) -> int:
    """Orchestrate download → spatial processing → PostGIS load."""
    source_url = url or DEFAULT_GIS_URL
    temp_path: Path | None = None

    try:
        temp_path = fetch_data(source_url)
        gdf = process_with_geopandas(temp_path)
        if gdf.geometry.name != "geometry":
            gdf = gdf.rename_geometry("geometry")
        return load_to_postgres(gdf)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
            extracted_dir = temp_path.parent / "extracted"
            if extracted_dir.exists():
                shutil.rmtree(extracted_dir, ignore_errors=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Ingest agricultural GIS zones into PostGIS raw layer"
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Override GIS download URL (defaults to GIS_AGRICULTURAL_ZONES_URL env var)",
    )
    args = parser.parse_args()
    run(url=args.url)


if __name__ == "__main__":
    main()
