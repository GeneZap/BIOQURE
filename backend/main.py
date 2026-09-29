"""BIOQURE FastAPI server.

The current demo exposes the BIOQURE API under /bioqure/*.
Legacy GeneZap modules are not imported during startup.
"""
from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.bioqure.router import router as bioqure_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
    force=True,
)

log = logging.getLogger("bioqure.main")

app = FastAPI(
    title="BIOQURE API",
    version="1.0.0",
    description=(
        "Research decision-support API for curated TCGA/GDC expression "
        "datasets and classical/quantum machine-learning inference."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bioqure_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "BIOQURE API",
        "status": "ok",
        "docs": "/docs",
        "bioqure_status": "/bioqure/status",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "bioqure",
    }


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {
        "status": "live",
        "service": "bioqure",
    }


__all__ = ["app", "root", "health", "health_live"]
