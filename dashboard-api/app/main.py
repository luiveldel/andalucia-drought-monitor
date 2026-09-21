"""FastAPI app — JSON for React dashboard; reads marts only."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import get_engine, load_dashboard_data
from app.spi_gis import (
    load_agricultural_zones_geojson,
    load_province_compare,
    load_provinces_geojson,
    load_spi_latest,
)

app = FastAPI(title="Andalusia drought dashboard API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def get_dashboard() -> dict:
    """Single payload for dashboard UI (includes provisional SPI when available)."""
    try:
        payload = load_dashboard_data()
        with get_engine().connect() as conn:
            payload["spi"] = load_spi_latest(conn)
        # Honest notes for UI
        notes = list(payload.get("data_notes") or [])
        spi = payload.get("spi") or {}
        if spi.get("caveat_es") and spi["caveat_es"] not in notes:
            notes.append(spi["caveat_es"])
        payload["data_notes"] = notes
        return jsonable_encoder(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/spi")
def get_spi() -> dict:
    """Latest provisional SPI-12 (or best available window) per province."""
    try:
        with get_engine().connect() as conn:
            return jsonable_encoder(load_spi_latest(conn))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/compare")
def compare_provinces(
    a: str = Query(..., min_length=2, description="Provincia A"),
    b: str = Query(..., min_length=2, description="Provincia B"),
) -> dict:
    """Comparativa lado a lado provincia A vs B (datos vivos de marts)."""
    if a.strip().lower() == b.strip().lower():
        raise HTTPException(status_code=400, detail="Elige dos provincias distintas.")
    try:
        with get_engine().connect() as conn:
            return jsonable_encoder(load_province_compare(conn, a.strip(), b.strip()))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/gis/provinces.geojson")
def gis_provinces() -> JSONResponse:
    """Andalusian province polygons from dim_provinces_polygons."""
    try:
        with get_engine().connect() as conn:
            fc = load_provinces_geojson(conn)
        return JSONResponse(content=fc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/gis/agricultural-zones.geojson")
def gis_zones() -> JSONResponse:
    """GIS agricultural zones / province boundaries overlay (cod_ccaa=01)."""
    try:
        with get_engine().connect() as conn:
            fc = load_agricultural_zones_geojson(conn)
        return JSONResponse(content=fc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/gis/chg/layers")
def gis_chg_layers() -> dict:
    """Catálogo de capas públicas CHG (metadatos; sin martillar GeoServer)."""
    try:
        from app.chg_layers import build_chg_layers_snapshot

        return jsonable_encoder(build_chg_layers_snapshot(include_inline_geojson=False))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/gis/chg/{layer_id}.geojson")
def gis_chg_layer_geojson(
    layer_id: str,
    refresh: bool = Query(False, description="Forzar refetch (ignora caché)"),
    max_features: int | None = Query(
        None, ge=1, le=5000, description="Tope WFS (obligatorio para recintos_riego_pub)"
    ),
    bbox: str | None = Query(
        None, description="BBOX WFS opcional: minx,miny,maxx,maxy[,CRS]"
    ),
    simplify_tol: float | None = Query(
        None, ge=0.0, le=0.1, description="Tolerancia Douglas-Peucker en grados"
    ),
) -> JSONResponse:
    """GeoJSON simplificado + metadatos de una capa CHG (caché disco/memoria)."""
    try:
        from app.chg_layers import LAYER_BY_ID, fetch_layer_geojson

        if layer_id not in LAYER_BY_ID:
            raise HTTPException(
                status_code=404,
                detail=f"Capa desconocida: {layer_id}. Ver /api/gis/chg/layers",
            )
        payload = fetch_layer_geojson(
            layer_id,
            force_refresh=refresh,
            max_features=max_features,
            bbox=bbox,
            simplify_tol=simplify_tol,
        )
        return JSONResponse(content=jsonable_encoder(payload))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/api/meteo/forecast")
def get_meteo_forecast(
    province: str | None = Query(
        None,
        description="Provincia andaluza (capital AEMET). Vacío = Andalucía.",
    ),
) -> dict:
    """AEMET (preferred) / Open-Meteo forecast for Andalucía or a province capital."""
    try:
        from app.meteo_forecast import load_meteo_forecast

        return jsonable_encoder(load_meteo_forecast(province))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/meteo/provinces")
def get_meteo_provinces() -> dict:
    """Province options for the Clima selector."""
    from app.provinces_meta import PROVINCES, REGIONAL_KEY

    return {
        "regional": REGIONAL_KEY,
        "provinces": [p["name"] for p in PROVINCES],
    }

