"""Pydantic models for dataset pool API contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PoolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=2000)


class PoolSummary(BaseModel):
    pool_id: str
    name: str
    description: str
    file_count: int
    manifest_version: int
    created_at: str
    updated_at: str


class PoolFileEntry(BaseModel):
    file_id: str
    original_filename: str
    size_bytes: int
    sha256: str | None = None


class PoolDetail(BaseModel):
    pool_id: str
    name: str
    description: str
    manifest_version: int
    created_at: str
    updated_at: str
    files: list[PoolFileEntry]
    version_history: list[dict[str, Any]] = Field(default_factory=list)


class ImportPathRequest(BaseModel):
    """Import FASTA from a server directory (requires GENEZAP_ALLOW_DATASET_PATH_IMPORT)."""

    source_directory: str = Field(..., min_length=1, max_length=4096)


class SnapshotRequest(BaseModel):
    label: str = Field("", max_length=500)


class BatchAnalyzeRequest(BaseModel):
    file_ids: list[str] = Field(..., min_length=1, max_length=500)
    pitch_demo: bool = False
    use_integrated_real: bool = False


class BatchJobStatus(BaseModel):
    job_id: str
    status: str
    pool_id: str
    total: int
    completed: int
    failed: int
    errors: list[dict[str, str]] = Field(default_factory=list)
