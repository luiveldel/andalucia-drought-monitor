"""FastAPI app — JSON for React dashboard; reads marts only."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from app.db import load_dashboard_data

app = FastAPI(title="Andalusia drought dashboard API", version="0.1.0")

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
    """Single payload for dashboard UI (same shape as former Reflex state load)."""
    try:
        payload = load_dashboard_data()
        return jsonable_encoder(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
