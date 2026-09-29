"""Paths for dataset pool storage (filesystem today; S3/R2-compatible via GENEZAP_DATASETS_ROOT indirection)."""

from __future__ import annotations

import os
from pathlib import Path

from genezap_settings import path_import_allowed

_ENV_ROOT = "GENEZAP_DATASETS_ROOT"

__all__ = ["get_datasets_root", "path_import_allowed"]


def get_datasets_root() -> Path:
    """
    Root directory for pools and batch jobs.

    Set GENEZAP_DATASETS_ROOT to a writable volume in containers (e.g. /data/datasets).
    Default: repository `data/datasets` (repo root parent of `backend/`).
    """
    raw = os.environ.get(_ENV_ROOT, "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    backend_dir = Path(__file__).resolve().parent.parent
    return (backend_dir.parent / "data" / "datasets").resolve()
