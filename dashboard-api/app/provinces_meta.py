"""Andalusian provinces: AEMET municipal codes (capitals) + Open-Meteo coords."""

from __future__ import annotations

from typing import Any

# Regional / default selection key in the UI
REGIONAL_KEY = "Andalucía"

# Capitals — INE municipality codes for AEMET municipal forecast
PROVINCES: list[dict[str, Any]] = [
    {"name": "Almería", "aemet_municipio": "04013", "lat": 36.8381, "lon": -2.4597},
    {"name": "Cádiz", "aemet_municipio": "11012", "lat": 36.5271, "lon": -6.2886},
    {"name": "Córdoba", "aemet_municipio": "14021", "lat": 37.8882, "lon": -4.7794},
    {"name": "Granada", "aemet_municipio": "18087", "lat": 37.1773, "lon": -3.5986},
    {"name": "Huelva", "aemet_municipio": "21041", "lat": 37.2614, "lon": -6.9447},
    {"name": "Jaén", "aemet_municipio": "23050", "lat": 37.7796, "lon": -3.7849},
    {"name": "Málaga", "aemet_municipio": "29067", "lat": 36.7213, "lon": -4.4214},
    {"name": "Sevilla", "aemet_municipio": "41091", "lat": 37.3891, "lon": -5.9845},
]

PROVINCE_BY_NAME = {p["name"]: p for p in PROVINCES}


def resolve_province(name: str | None) -> dict[str, Any] | None:
    """Return province meta or None for regional Andalucía."""
    if not name:
        return None
    key = name.strip()
    if key.lower() in ("andalucía", "andalucia", "all", "regional"):
        return None
    return PROVINCE_BY_NAME.get(key)
