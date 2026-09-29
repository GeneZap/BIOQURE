"""
Central environment-driven settings for GeneZap API.

Design goals:
- Single place for deployment-related env vars (Render/Fly/Vercel).
- Production mode disables unsafe defaults (path import, permissive CORS).
- Numeric limits are overridable for free-tier hosts without code changes.

Future: swap filesystem paths for S3/R2 URIs; add DATABASE_URL for PostgreSQL;
      add REDIS_URL for Celery without changing call sites that read these helpers.
"""

from __future__ import annotations

import os
from functools import lru_cache


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@lru_cache(maxsize=1)
def is_production() -> bool:
    """True when GENEZAP_ENV indicates a deployed / non-local profile."""
    v = os.environ.get("GENEZAP_ENV", "").strip().lower()
    return v in ("production", "prod", "staging")


def cors_allow_origins() -> list[str]:
    """
    Comma-separated GENEZAP_CORS_ORIGINS, e.g. https://genezap.vercel.app,http://localhost:5173
    If unset, defaults to wildcard * (credentials must stay false — see cors_allow_credentials).
    """
    raw = os.environ.get("GENEZAP_CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["*"]


def cors_allow_origin_regex() -> str | None:
        """
        Optional regex-based CORS allowlist.

        Useful for Vercel preview deployments where hostnames change per branch/commit.
        Example:
            ^https://genezap(-[a-z0-9-]+)?-the-nityant-s-projects\\.vercel\\.app$
        """
        raw = os.environ.get("GENEZAP_CORS_ORIGIN_REGEX", "").strip()
        return raw or None


def cors_allow_credentials() -> bool:
    """Browser CORS: credentials with wildcard origin is invalid — keep False when using *."""
    origins = cors_allow_origins()
    if any(o == "*" for o in origins):
        return False
    return _env_bool("GENEZAP_CORS_CREDENTIALS", default=False)


def max_upload_bytes() -> int:
    """Single-request body budget hint (multipart FASTA); enforced in middleware + handlers."""
    mb = _env_int("GENEZAP_MAX_UPLOAD_MB", 100)
    return max(1, mb) * 1024 * 1024


def max_pool_upload_bytes() -> int:
    """Per-file limit for dataset pool uploads (defaults to same as max_upload_bytes)."""
    mb = _env_int("GENEZAP_MAX_POOL_FILE_MB", 0)
    if mb <= 0:
        return max_upload_bytes()
    return max(1, mb) * 1024 * 1024


def max_pool_files_per_request() -> int:
    return max(1, _env_int("GENEZAP_MAX_POOL_FILES_PER_REQUEST", 25))


def max_batch_job_files() -> int:
    return max(1, _env_int("GENEZAP_MAX_BATCH_FILES", 50))


def path_import_allowed() -> bool:
    """Never allow server-side arbitrary path reads in production, regardless of flags."""
    if is_production():
        return False
    return _env_bool("GENEZAP_ALLOW_DATASET_PATH_IMPORT", default=False)


def allow_integrated_real() -> bool:
    """Allow the heavyweight integrated artifact stack only when explicitly enabled."""
    if is_production():
        return _env_bool("GENEZAP_ALLOW_INTEGRATED_REAL", default=False)
    return _env_bool("GENEZAP_ALLOW_INTEGRATED_REAL", default=True)


def log_level() -> str:
    return os.environ.get("GENEZAP_LOG_LEVEL", "INFO").strip().upper() or "INFO"
