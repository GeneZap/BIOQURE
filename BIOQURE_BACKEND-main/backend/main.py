"""BIOQURE FastAPI server.

BIOQURE exposes the curated public TCGA/GDC expression dataset API and
model-inference API under /bioqure/*.

The legacy GeneZap FASTA endpoints are intentionally not imported here.
This keeps BIOQURE startup independent of the old antimicrobial-resistance
analysis stack.
"""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.bioqure.router import router as bioqure_router


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
    force=True,
)

log = logging.getLogger("bioqure.main")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BIOQURE API",
    version="1.0.0",
    description=(
        "Research decision-support API for curated TCGA/GDC expression "
        "datasets and classical/quantum machine-learning inference."
    ),
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

# Local development defaults for the Vite frontend.
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


# ---------------------------------------------------------------------------
# BIOQURE routes
# ---------------------------------------------------------------------------

app.include_router(bioqre_router)


# ---------------------------------------------------------------------------
# Basic health endpoints
# ---------------------------------------------------------------------------

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


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "BIOQURE API",
        "status": "ok",
        "docs": "/docs",
        "bioqure_status": "/bioqure/status",
    }


__all__ = [
    "app",
    "health",
    "health_live",
    "root",
]