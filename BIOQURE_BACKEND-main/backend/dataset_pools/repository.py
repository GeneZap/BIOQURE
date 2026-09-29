"""Filesystem repository for pool manifests and FASTA blobs."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dataset_pools.config import get_datasets_root
from dataset_pools.validation import validate_fasta_bytes

_MANIFEST_NAME = "pool_manifest.json"
_FILES_DIR = "files"
_FASTA_SUFFIXES = (".fna", ".fasta", ".fa")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    base = Path(name).name
    if not base or base in (".", ".."):
        return "sequence.fasta"
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)[:180]
    return cleaned or "sequence.fasta"


class DatasetRepository:
    """CRUD for pools under GENEZAP_DATASETS_ROOT/pools/{pool_id}/."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_datasets_root()
        self.pools_root = self.root / "pools"
        self.jobs_root = self.root / "jobs"

    def ensure_layout(self) -> None:
        self.pools_root.mkdir(parents=True, exist_ok=True)
        self.jobs_root.mkdir(parents=True, exist_ok=True)

    def _pool_dir(self, pool_id: str) -> Path:
        return self.pools_root / pool_id

    def _manifest_path(self, pool_id: str) -> Path:
        return self._pool_dir(pool_id) / _MANIFEST_NAME

    def _files_dir(self, pool_id: str) -> Path:
        return self._pool_dir(pool_id) / _FILES_DIR

    def create_pool(self, name: str, description: str = "") -> dict[str, Any]:
        self.ensure_layout()
        pool_id = str(uuid.uuid4())
        pdir = self._pool_dir(pool_id)
        pdir.mkdir(parents=False, exist_ok=False)
        (pdir / _FILES_DIR).mkdir(parents=False, exist_ok=True)
        now = _utc_now_iso()
        manifest: dict[str, Any] = {
            "pool_id": pool_id,
            "name": name.strip(),
            "description": (description or "").strip(),
            "created_at": now,
            "updated_at": now,
            "manifest_version": 1,
            "files": [],
            "version_history": [{"version": 1, "at": now, "label": "initial"}],
        }
        self._write_manifest(pool_id, manifest)
        return manifest

    def _write_manifest(self, pool_id: str, manifest: dict[str, Any]) -> None:
        path = self._manifest_path(pool_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _read_manifest(self, pool_id: str) -> dict[str, Any]:
        path = self._manifest_path(pool_id)
        if not path.is_file():
            raise FileNotFoundError(pool_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def list_pools(self) -> list[dict[str, Any]]:
        self.ensure_layout()
        out: list[dict[str, Any]] = []
        for child in sorted(self.pools_root.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            mid = child / _MANIFEST_NAME
            if not mid.is_file():
                continue
            try:
                m = json.loads(mid.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            out.append(
                {
                    "pool_id": m.get("pool_id", child.name),
                    "name": m.get("name", child.name),
                    "description": m.get("description", ""),
                    "file_count": len(m.get("files") or []),
                    "manifest_version": int(m.get("manifest_version", 1)),
                    "created_at": m.get("created_at", ""),
                    "updated_at": m.get("updated_at", ""),
                }
            )
        return out

    def get_pool(self, pool_id: str) -> dict[str, Any]:
        return self._read_manifest(pool_id)

    def add_file_bytes(
        self,
        pool_id: str,
        original_filename: str,
        data: bytes,
        *,
        max_bytes: int,
    ) -> dict[str, Any]:
        lower = original_filename.lower()
        if not any(lower.endswith(s) for s in _FASTA_SUFFIXES):
            raise ValueError("Only .fna, .fasta, or .fa are accepted")
        validate_fasta_bytes(data, max_bytes=max_bytes)
        manifest = self._read_manifest(pool_id)
        file_id = str(uuid.uuid4())
        safe = _safe_filename(original_filename)
        stored_name = f"{file_id}_{safe}"
        dest = self._files_dir(pool_id) / stored_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        h = hashlib.sha256(data).hexdigest()
        entry = {
            "file_id": file_id,
            "original_filename": Path(original_filename).name,
            "size_bytes": len(data),
            "sha256": h,
            "relative_path": f"{_FILES_DIR}/{stored_name}",
        }
        files = list(manifest.get("files") or [])
        files.append(entry)
        manifest["files"] = files
        manifest["updated_at"] = _utc_now_iso()
        self._write_manifest(pool_id, manifest)
        return entry

    def read_file_bytes(self, pool_id: str, file_id: str) -> tuple[bytes, str]:
        manifest = self._read_manifest(pool_id)
        for f in manifest.get("files") or []:
            if f.get("file_id") == file_id:
                rel = f.get("relative_path") or ""
                path = self._pool_dir(pool_id) / rel
                if not path.is_file():
                    raise FileNotFoundError(str(path))
                return path.read_bytes(), str(f.get("original_filename", path.name))
        raise KeyError(file_id)

    def remove_file(self, pool_id: str, file_id: str) -> None:
        manifest = self._read_manifest(pool_id)
        files = list(manifest.get("files") or [])
        new_files = []
        removed = False
        for f in files:
            if f.get("file_id") == file_id:
                rel = f.get("relative_path") or ""
                path = self._pool_dir(pool_id) / rel
                if path.is_file():
                    path.unlink()
                removed = True
                continue
            new_files.append(f)
        if not removed:
            raise KeyError(file_id)
        manifest["files"] = new_files
        manifest["updated_at"] = _utc_now_iso()
        self._write_manifest(pool_id, manifest)

    def bump_manifest_version(self, pool_id: str, label: str = "") -> dict[str, Any]:
        manifest = self._read_manifest(pool_id)
        v = int(manifest.get("manifest_version", 1)) + 1
        manifest["manifest_version"] = v
        hist = list(manifest.get("version_history") or [])
        hist.append({"version": v, "at": _utc_now_iso(), "label": label or "snapshot"})
        manifest["version_history"] = hist
        manifest["updated_at"] = _utc_now_iso()
        snap_dir = self._pool_dir(pool_id) / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap_path = snap_dir / f"v{v}.json"
        snap_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self._write_manifest(pool_id, manifest)
        return manifest

    def import_from_directory(self, pool_id: str, source: Path, *, max_bytes: int) -> list[dict[str, Any]]:
        """Copy eligible FASTA files from source into pool. Returns new file entries."""
        if not source.is_dir():
            raise NotADirectoryError(str(source))
        added: list[dict[str, Any]] = []
        for p in sorted(source.iterdir()):
            if not p.is_file():
                continue
            if p.name.startswith("."):
                continue
            low = p.name.lower()
            if not any(low.endswith(s) for s in _FASTA_SUFFIXES):
                continue
            data = p.read_bytes()
            added.append(self.add_file_bytes(pool_id, p.name, data, max_bytes=max_bytes))
        return added

    def delete_pool(self, pool_id: str) -> None:
        pdir = self._pool_dir(pool_id)
        if pdir.is_dir():
            shutil.rmtree(pdir, ignore_errors=True)
