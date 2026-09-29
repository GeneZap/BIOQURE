"""FastAPI routes for dataset pools — does not replace POST /analyze."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile

from analysis import analyze_sequence_bytes
from dataset_pools.batch_jobs import BatchJobManager
from dataset_pools.config import get_datasets_root, path_import_allowed
from dataset_pools.models import (
    BatchAnalyzeRequest,
    BatchJobStatus,
    ImportPathRequest,
    PoolCreate,
    PoolDetail,
    PoolFileEntry,
    PoolSummary,
    SnapshotRequest,
)
from dataset_pools.repository import DatasetRepository
from genezap_settings import (
    is_production,
    max_batch_job_files,
    max_pool_files_per_request,
    max_pool_upload_bytes,
    max_upload_bytes,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])

_repo = DatasetRepository()
_jobs = BatchJobManager(_repo)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _require_uuid(label: str, value: str) -> None:
    if not _UUID_RE.match(value or ""):
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


def _manifest_to_detail(m: dict[str, Any]) -> PoolDetail:
    files = [
        PoolFileEntry(
            file_id=str(f["file_id"]),
            original_filename=str(f["original_filename"]),
            size_bytes=int(f["size_bytes"]),
            sha256=f.get("sha256"),
        )
        for f in m.get("files") or []
    ]
    return PoolDetail(
        pool_id=str(m["pool_id"]),
        name=str(m["name"]),
        description=str(m.get("description", "")),
        manifest_version=int(m.get("manifest_version", 1)),
        created_at=str(m.get("created_at", "")),
        updated_at=str(m.get("updated_at", "")),
        files=files,
        version_history=list(m.get("version_history") or []),
    )


def _run_analyze_bytes(
    _pool_id: str,
    _file_id: str,
    raw: bytes,
    _orig_name: str,
    pitch_demo: bool,
    use_integrated_real: bool,
) -> dict[str, Any]:
    """Thin wrapper so batch jobs reuse the same inference stack."""
    return analyze_sequence_bytes(raw, pitch_demo=pitch_demo, use_integrated_real=use_integrated_real)


@router.post("/pools", response_model=PoolDetail)
def create_pool(body: PoolCreate) -> PoolDetail:
    m = _repo.create_pool(body.name, body.description)
    return _manifest_to_detail(m)


@router.get("/pools", response_model=list[PoolSummary])
def list_pools() -> list[PoolSummary]:
    rows = _repo.list_pools()
    return [PoolSummary(**r) for r in rows]


@router.get("/pools/default")
def get_default_pool() -> PoolDetail:
    """
    Get the pre-loaded public dataset pool
    All users can view and analyze these ~295 reference genomes without creating a pool
    """
    pool_id = "default-public-pool"
    try:
        m = _repo.get_pool(pool_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Default pool not initialized. Run populate_default_pool.py"
        ) from None
    return _manifest_to_detail(m)


@router.get("/pools/{pool_id}", response_model=PoolDetail)
def get_pool(pool_id: str) -> PoolDetail:
    # Handle default public pool specially (read-only, no UUID required)
    if pool_id != "default-public-pool":
        _require_uuid("pool_id", pool_id)
    try:
        m = _repo.get_pool(pool_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pool not found") from None
    return _manifest_to_detail(m)


@router.delete("/pools/{pool_id}", status_code=204)
def delete_pool(pool_id: str) -> None:
    _require_uuid("pool_id", pool_id)
    try:
        _repo.get_pool(pool_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pool not found") from None
    _repo.delete_pool(pool_id)


@router.post("/pools/{pool_id}/files", response_model=list[PoolFileEntry])
async def upload_files(
    pool_id: str,
    files: Annotated[list[UploadFile], File(description="One or more FASTA files (repeat form field 'files').")],
) -> list[PoolFileEntry]:
    _require_uuid("pool_id", pool_id)
    try:
        _repo.get_pool(pool_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Pool not found") from e
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    per_req = max_pool_files_per_request()
    if len(files) > per_req:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files in one request (max {per_req}). Increase GENEZAP_MAX_POOL_FILES_PER_REQUEST if needed.",
        )
    out: list[PoolFileEntry] = []
    max_b = max_pool_upload_bytes()
    for uf in files:
        if not uf.filename:
            continue
        raw = await uf.read()
        if len(raw) > max_b:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds per-file limit ({max_b // (1024 * 1024)} MiB).",
            )
        try:
            entry = _repo.add_file_bytes(pool_id, uf.filename, raw, max_bytes=max_b)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        out.append(
            PoolFileEntry(
                file_id=entry["file_id"],
                original_filename=entry["original_filename"],
                size_bytes=int(entry["size_bytes"]),
                sha256=entry.get("sha256"),
            )
        )
    return out


@router.delete("/pools/{pool_id}/files/{file_id}", status_code=204)
def delete_file(pool_id: str, file_id: str) -> None:
    _require_uuid("pool_id", pool_id)
    _require_uuid("file_id", file_id)
    try:
        _repo.remove_file(pool_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pool not found") from None
    except KeyError:
        raise HTTPException(status_code=404, detail="File not found in pool") from None


@router.post("/pools/{pool_id}/snapshot", response_model=PoolDetail)
def snapshot_manifest(pool_id: str, body: SnapshotRequest | None = None) -> PoolDetail:
    _require_uuid("pool_id", pool_id)
    try:
        m = _repo.bump_manifest_version(pool_id, (body or SnapshotRequest()).label)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pool not found") from None
    return _manifest_to_detail(m)


@router.post("/pools/{pool_id}/import-path", response_model=list[PoolFileEntry])
def import_path(pool_id: str, body: ImportPathRequest) -> list[PoolFileEntry]:
    _require_uuid("pool_id", pool_id)
    if not path_import_allowed():
        msg = "Server-side path import is disabled"
        if is_production():
            msg += " in production (GENEZAP_ENV)."
        else:
            msg += ". Set GENEZAP_ALLOW_DATASET_PATH_IMPORT=1 for local development only."
        raise HTTPException(status_code=403, detail=msg)
    try:
        _repo.get_pool(pool_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pool not found") from None
    src = Path(body.source_directory).expanduser()
    max_b = max_pool_upload_bytes()
    try:
        added = _repo.import_from_directory(pool_id, src.resolve(), max_bytes=max_b)
    except (OSError, NotADirectoryError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return [
        PoolFileEntry(
            file_id=a["file_id"],
            original_filename=a["original_filename"],
            size_bytes=int(a["size_bytes"]),
            sha256=a.get("sha256"),
        )
        for a in added
    ]


@router.post("/pools/{pool_id}/files/{file_id}/analyze")
async def analyze_pool_file(
    pool_id: str,
    file_id: str,
    pitch_demo: bool = Query(False),
    use_integrated_real: bool = Query(False),
) -> dict[str, Any]:
    # Handle default public pool specially (read-only, no UUID required)
    if pool_id != "default-public-pool":
        _require_uuid("pool_id", pool_id)
    _require_uuid("file_id", file_id)
    try:
        raw, _ = _repo.read_file_bytes(pool_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pool or file not found") from None
    except KeyError:
        raise HTTPException(status_code=404, detail="File not found in pool") from None
    if len(raw) > max_upload_bytes():
        raise HTTPException(status_code=413, detail="Stored file exceeds configured analyze size limit.")
    try:
        return analyze_sequence_bytes(raw, pitch_demo=pitch_demo, use_integrated_real=use_integrated_real)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/pools/{pool_id}/batch-jobs", response_model=dict[str, str])
def start_batch_job(
    pool_id: str,
    body: BatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    # Handle default public pool specially (read-only, no UUID required)
    if pool_id != "default-public-pool":
        _require_uuid("pool_id", pool_id)
    max_b = max_batch_job_files()
    if len(body.file_ids) > max_b:
        raise HTTPException(
            status_code=400,
            detail=f"Too many file_ids for one batch job (max {max_b}).",
        )
    try:
        _repo.get_pool(pool_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pool not found") from None
    lim = max_upload_bytes()
    for fid in body.file_ids:
        _require_uuid("file_id", fid)
        try:
            raw, _ = _repo.read_file_bytes(pool_id, fid)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Unknown file_id in pool: {fid}") from None
        except FileNotFoundError:
            raise HTTPException(status_code=400, detail=f"Missing file on disk for id {fid}") from None
        if len(raw) > lim:
            raise HTTPException(
                status_code=400,
                detail=f"File {fid} exceeds analyze byte limit; reduce GENEZAP_MAX_UPLOAD_MB or split input.",
            )
    job_id = _jobs.create_job(pool_id, body.file_ids)

    def _task() -> None:
        _jobs.run_job(
            job_id,
            _run_analyze_bytes,
            pitch_demo=body.pitch_demo,
            use_integrated_real=body.use_integrated_real,
        )

    background_tasks.add_task(_task)
    return {"job_id": job_id}


@router.get("/batch-jobs/{job_id}", response_model=BatchJobStatus)
def batch_job_status(job_id: str) -> BatchJobStatus:
    _require_uuid("job_id", job_id)
    try:
        m = _jobs.get_status(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found") from None
    return BatchJobStatus(
        job_id=str(m["job_id"]),
        status=str(m["status"]),
        pool_id=str(m["pool_id"]),
        total=int(m["total"]),
        completed=int(m["completed"]),
        failed=int(m["failed"]),
        errors=[dict(e) for e in m.get("errors") or []],
    )


@router.get("/batch-jobs/{job_id}/results/{file_id}")
def batch_job_result(job_id: str, file_id: str) -> dict[str, Any]:
    _require_uuid("job_id", job_id)
    _require_uuid("file_id", file_id)
    data = _jobs.read_result_json(job_id, file_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Result not found (job may still be running).")
    return data


@router.get("/config/hints")
def deployment_hints() -> dict[str, Any]:
    """Non-secret deployment hints for operators (frontend may ignore)."""
    root = get_datasets_root()
    return {
        "datasets_root": str(root),
        "production": is_production(),
        "path_import_enabled": path_import_allowed(),
        "max_upload_mb": max_upload_bytes() // (1024 * 1024),
        "max_pool_file_mb": max_pool_upload_bytes() // (1024 * 1024),
        "max_pool_files_per_request": max_pool_files_per_request(),
        "max_batch_files": max_batch_job_files(),
    }
