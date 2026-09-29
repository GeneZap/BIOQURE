"""Filesystem-backed batch analysis jobs (durable across single-worker restarts for completed jobs)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dataset_pools.config import get_datasets_root
from dataset_pools.repository import DatasetRepository

JobRunner = Callable[[str, str, bytes, str, bool, bool], dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BatchJobManager:
    """Stores job meta under data/datasets/jobs/{job_id}/."""

    def __init__(self, repo: DatasetRepository | None = None) -> None:
        self.repo = repo or DatasetRepository()
        self.root = self.repo.jobs_root
        self._lock = threading.Lock()
        self._running: set[str] = set()

    def _job_dir(self, job_id: str) -> Path:
        return self.root / job_id

    def create_job(self, pool_id: str, file_ids: list[str]) -> str:
        self.repo.ensure_layout()
        job_id = str(uuid.uuid4())
        jdir = self._job_dir(job_id)
        jdir.mkdir(parents=False, exist_ok=False)
        meta = {
            "job_id": job_id,
            "pool_id": pool_id,
            "file_ids": file_ids,
            "status": "pending",
            "total": len(file_ids),
            "completed": 0,
            "failed": 0,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "errors": [],
        }
        (jdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (jdir / "results").mkdir(exist_ok=True)
        return job_id

    def _read_meta(self, job_id: str) -> dict[str, Any]:
        path = self._job_dir(job_id) / "meta.json"
        if not path.is_file():
            raise FileNotFoundError(job_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_meta(self, job_id: str, meta: dict[str, Any]) -> None:
        meta["updated_at"] = _now_iso()
        path = self._job_dir(job_id) / "meta.json"
        path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def get_status(self, job_id: str) -> dict[str, Any]:
        return self._read_meta(job_id)

    def run_job(
        self,
        job_id: str,
        run_analyze: JobRunner,
        *,
        pitch_demo: bool,
        use_integrated_real: bool,
    ) -> None:
        """Execute job synchronously (call from thread or BackgroundTasks)."""
        with self._lock:
            if job_id in self._running:
                return
            self._running.add(job_id)
        try:
            meta = self._read_meta(job_id)
            meta["status"] = "running"
            self._write_meta(job_id, meta)
            pool_id = meta["pool_id"]
            file_ids: list[str] = meta["file_ids"]
            jdir = self._job_dir(job_id)
            errors: list[dict[str, str]] = []
            completed = 0
            failed = 0
            for fid in file_ids:
                try:
                    raw, orig_name = self.repo.read_file_bytes(pool_id, fid)
                    payload = run_analyze(pool_id, fid, raw, orig_name, pitch_demo, use_integrated_real)
                    (jdir / "results" / f"{fid}.json").write_text(
                        json.dumps(payload, indent=2),
                        encoding="utf-8",
                    )
                    completed += 1
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    errors.append({"file_id": fid, "detail": str(e)})
                meta = self._read_meta(job_id)
                meta["completed"] = completed
                meta["failed"] = failed
                meta["errors"] = errors
                self._write_meta(job_id, meta)
            meta = self._read_meta(job_id)
            meta["status"] = "completed" if failed == 0 else "completed"
            meta["errors"] = errors
            self._write_meta(job_id, meta)
        except Exception as e:  # noqa: BLE001
            meta = self._read_meta(job_id)
            meta["status"] = "failed"
            meta["errors"] = meta.get("errors", []) + [{"file_id": "*", "detail": str(e)}]
            self._write_meta(job_id, meta)
        finally:
            with self._lock:
                self._running.discard(job_id)

    def list_result_files(self, job_id: str) -> list[str]:
        rdir = self._job_dir(job_id) / "results"
        if not rdir.is_dir():
            return []
        return sorted(p.name for p in rdir.glob("*.json"))

    def read_result_json(self, job_id: str, file_id: str) -> dict[str, Any] | None:
        path = self._job_dir(job_id) / "results" / f"{file_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
