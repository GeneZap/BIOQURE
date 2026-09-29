"""
BIOQURE public dataset repository.

Stores and reads the curated public TCGA/GDC dataset pool from the backend
filesystem. This module is storage/catalog only; preprocessing and inference
are handled by the other BIOQURE modules.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_datasets_root


MANIFEST_FILENAME = "manifest.json"
EXPRESSION_FILENAME = "expression.tsv"
METADATA_FILENAME = "metadata.json"

_DATASET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_dataset_id(dataset_id: str) -> str:
    value = str(dataset_id or "").strip()

    if not value:
        raise ValueError("BIOQURE dataset_id cannot be empty.")

    if not _DATASET_ID_RE.fullmatch(value):
        raise ValueError(
            "Invalid BIOQURE dataset_id. Use 1-64 characters containing "
            "letters, numbers, '_' or '-'."
        )

    return value


def _safe_relative_path(relative_path: str) -> Path:
    raw = str(relative_path or "").strip()

    if not raw:
        raise ValueError("Manifest relative_path cannot be empty.")

    path = Path(raw)

    if path.is_absolute() or any(
        part in ("", ".", "..") for part in path.parts
    ):
        raise ValueError(
            f"Unsafe manifest relative_path: {relative_path!r}"
        )

    return path


class BIOQUREPublicDatasetRepository:
    """
    Filesystem repository for the BIOQURE public TCGA/GDC pool.

    Default location:
        <GENEZAP_DATASETS_ROOT>/public/

    Expected dataset layout:

        data/datasets/public/
            manifest.json
            BRCA_001/
                expression.tsv
                metadata.json
            BRCA_002/
                expression.tsv
                metadata.json
            ...
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(
            root or get_datasets_root()
        ).expanduser().resolve()

        self.public_root = self.root / "public"
        self.manifest_path = self.public_root / MANIFEST_FILENAME

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def ensure_layout(self) -> None:
        self.public_root.mkdir(parents=True, exist_ok=True)

    def dataset_dir(self, dataset_id: str) -> Path:
        safe_id = _safe_dataset_id(dataset_id)

        public_root = self.public_root.resolve()
        path = (public_root / safe_id).resolve()

        try:
            path.relative_to(public_root)
        except ValueError as exc:
            raise ValueError(
                "BIOQURE dataset path escaped the public dataset root."
            ) from exc

        return path

    def expression_path(self, dataset_id: str) -> Path:
        return self.dataset_dir(dataset_id) / EXPRESSION_FILENAME

    def metadata_path(self, dataset_id: str) -> Path:
        return self.dataset_dir(dataset_id) / METADATA_FILENAME

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def _default_manifest(self) -> dict[str, Any]:
        now = _utc_now_iso()

        return {
            "schema_version": 1,
            "collection_id": "bioqure-public-tcga",
            "name": "BIOQURE Public Dataset Pool",
            "description": (
                "Curated public TCGA/GDC expression datasets prepared "
                "for BIOQURE research inference."
            ),
            "created_at": now,
            "updated_at": now,
            "datasets": [],
        }

    @staticmethod
    def _write_json_atomic(
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temp_path.replace(path)

    def load_manifest(self) -> dict[str, Any]:
        """
        Load the public manifest.

        If it does not exist yet, create an empty one.
        """
        self.ensure_layout()

        if not self.manifest_path.is_file():
            manifest = self._default_manifest()
            self._write_json_atomic(
                self.manifest_path,
                manifest,
            )
            return manifest

        try:
            data = json.loads(
                self.manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "BIOQURE public manifest contains invalid JSON: "
                f"{self.manifest_path}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "BIOQURE public manifest must be a JSON object."
            )

        datasets = data.get("datasets")

        if datasets is None:
            data["datasets"] = []
        elif not isinstance(datasets, list):
            raise ValueError(
                "BIOQURE public manifest 'datasets' must be a list."
            )

        return data

    def save_manifest(
        self,
        manifest: dict[str, Any],
    ) -> None:
        """
        Persist the public manifest.
        """
        if not isinstance(manifest, dict):
            raise ValueError("BIOQURE manifest must be a JSON object.")

        datasets = manifest.get("datasets")

        if datasets is None:
            manifest["datasets"] = []
        elif not isinstance(datasets, list):
            raise ValueError(
                "BIOQURE manifest 'datasets' must be a list."
            )

        manifest["schema_version"] = int(
            manifest.get("schema_version", 1)
        )
        manifest.setdefault(
            "collection_id",
            "bioqure-public-tcga",
        )
        manifest.setdefault(
            "name",
            "BIOQURE Public Dataset Pool",
        )
        manifest.setdefault(
            "description",
            "Curated public TCGA/GDC expression datasets.",
        )
        manifest.setdefault(
            "created_at",
            _utc_now_iso(),
        )
        manifest["updated_at"] = _utc_now_iso()

        self._write_json_atomic(
            self.manifest_path,
            manifest,
        )

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_dataset_record(
        record: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise ValueError(
                "Each BIOQURE dataset record must be an object."
            )

        dataset_id = _safe_dataset_id(
            str(record.get("dataset_id", ""))
        )

        result = dict(record)
        result["dataset_id"] = dataset_id

        result.setdefault("name", dataset_id)
        result.setdefault("project", "TCGA-BRCA")
        result.setdefault(
            "data_type",
            "RNA-seq gene expression",
        )
        result.setdefault("description", "")
        result.setdefault("access", "open")
        result.setdefault("gdc_file_id", "")
        result.setdefault("case_id", "")
        result.setdefault("sample_id", "")
        result.setdefault("original_filename", "")
        result.setdefault("download_filename", "")
        result.setdefault(
            "relative_path",
            f"{dataset_id}/{EXPRESSION_FILENAME}",
        )
        result.setdefault(
            "metadata_path",
            f"{dataset_id}/{METADATA_FILENAME}",
        )

        return result

    def list_public_datasets(self) -> list[dict[str, Any]]:
        manifest = self.load_manifest()

        datasets = [
            self._normalize_dataset_record(record)
            for record in (manifest.get("datasets") or [])
        ]

        datasets.sort(
            key=lambda row: row["dataset_id"].lower()
        )

        return datasets

    def get_public_dataset(
        self,
        dataset_id: str,
    ) -> dict[str, Any]:
        safe_id = _safe_dataset_id(dataset_id)

        for record in self.list_public_datasets():
            if record["dataset_id"] == safe_id:
                return record

        raise KeyError(safe_id)

    # ------------------------------------------------------------------
    # Safe file resolution
    # ------------------------------------------------------------------

    def _resolve_manifest_file(
        self,
        dataset_id: str,
        field_name: str,
    ) -> Path:
        record = self.get_public_dataset(dataset_id)

        relative = _safe_relative_path(
            str(record.get(field_name, ""))
        )

        public_root = self.public_root.resolve()
        path = (public_root / relative).resolve()

        try:
            path.relative_to(public_root)
        except ValueError as exc:
            raise ValueError(
                f"Manifest path for {dataset_id!r} escapes "
                "the public dataset root."
            ) from exc

        return path

    # ------------------------------------------------------------------
    # Dataset file access
    # ------------------------------------------------------------------

    def read_expression_bytes(
        self,
        dataset_id: str,
    ) -> tuple[bytes, str]:
        """
        Read one public expression file.

        Returns:
            (raw_bytes, download_filename)
        """
        safe_id = _safe_dataset_id(dataset_id)
        record = self.get_public_dataset(safe_id)

        path = self._resolve_manifest_file(
            safe_id,
            "relative_path",
        )

        if not path.is_file():
            raise FileNotFoundError(
                f"Expression file for {safe_id!r} was not found: {path}"
            )

        data = path.read_bytes()

        filename = str(
            record.get("download_filename")
            or record.get("original_filename")
            or path.name
        ).strip()

        return data, (filename or path.name)

    def read_dataset_metadata(
        self,
        dataset_id: str,
    ) -> dict[str, Any]:
        """
        Read optional per-dataset metadata.json.

        If the sidecar does not exist, return the manifest record.
        """
        safe_id = _safe_dataset_id(dataset_id)
        path = self.metadata_path(safe_id)

        if not path.is_file():
            return self.get_public_dataset(safe_id)

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid dataset metadata JSON: {path}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Dataset metadata must be a JSON object: {path}"
            )

        return data

    # ------------------------------------------------------------------
    # Population helper
    # ------------------------------------------------------------------

    def add_public_dataset(
        self,
        *,
        dataset_id: str,
        expression_bytes: bytes,
        metadata: dict[str, Any],
        expression_filename: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """
        Add one public dataset.

        This is intended for a local/admin population script.

        There is deliberately no unrestricted public upload endpoint
        using this method.
        """
        safe_id = _safe_dataset_id(dataset_id)

        if not expression_bytes:
            raise ValueError(
                f"Expression data for {safe_id} is empty."
            )

        if not isinstance(metadata, dict):
            raise ValueError(
                f"Metadata for {safe_id} must be an object."
            )

        dataset_dir = self.dataset_dir(safe_id)

        if dataset_dir.exists() and not overwrite:
            raise FileExistsError(
                f"BIOQURE public dataset already exists: {safe_id}"
            )

        dataset_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = Path(
            expression_filename or EXPRESSION_FILENAME
        ).name

        if not filename:
            filename = EXPRESSION_FILENAME

        expression_path = dataset_dir / filename
        expression_path.write_bytes(expression_bytes)

        sha256 = hashlib.sha256(
            expression_bytes
        ).hexdigest()

        record = dict(metadata)

        record["dataset_id"] = safe_id
        record.setdefault("name", safe_id)
        record.setdefault("project", "TCGA-BRCA")
        record.setdefault(
            "data_type",
            "RNA-seq gene expression",
        )
        record.setdefault("description", "")
        record.setdefault("access", "open")

        record["original_filename"] = str(
            metadata.get("original_filename")
            or metadata.get("filename")
            or expression_path.name
        )

        record["download_filename"] = str(
            metadata.get("download_filename")
            or record["original_filename"]
            or expression_path.name
        )

        record["relative_path"] = (
            f"{safe_id}/{expression_path.name}"
        )

        record["metadata_path"] = (
            f"{safe_id}/{METADATA_FILENAME}"
        )

        record["size_bytes"] = len(expression_bytes)
        record["sha256"] = sha256
        record["added_at"] = _utc_now_iso()

        self._write_json_atomic(
            dataset_dir / METADATA_FILENAME,
            record,
        )

        manifest = self.load_manifest()
        datasets = list(
            manifest.get("datasets") or []
        )

        replaced = False

        for index, existing in enumerate(datasets):
            if (
                isinstance(existing, dict)
                and str(
                    existing.get("dataset_id", "")
                ) == safe_id
            ):
                datasets[index] = record
                replaced = True
                break

        if not replaced:
            datasets.append(record)

        manifest["datasets"] = datasets
        self.save_manifest(manifest)

        return record

    # ------------------------------------------------------------------
    # Local/admin removal
    # ------------------------------------------------------------------

    def remove_public_dataset(
        self,
        dataset_id: str,
    ) -> None:
        """
        Remove one public dataset.

        Intended for local/admin maintenance only. No public API route
        should expose this operation.
        """
        safe_id = _safe_dataset_id(dataset_id)
        dataset_dir = self.dataset_dir(safe_id)

        manifest = self.load_manifest()
        datasets = list(
            manifest.get("datasets") or []
        )

        filtered = [
            row
            for row in datasets
            if not (
                isinstance(row, dict)
                and str(
                    row.get("dataset_id", "")
                ) == safe_id
            )
        ]

        if len(filtered) == len(datasets):
            raise KeyError(safe_id)

        manifest["datasets"] = filtered
        self.save_manifest(manifest)

        if dataset_dir.is_dir():
            shutil.rmtree(
                dataset_dir,
                ignore_errors=True,
            )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def count(self) -> int:
        return len(self.list_public_datasets())

    def public_catalog_summary(self) -> dict[str, Any]:
        datasets = self.list_public_datasets()

        projects = sorted(
            {
                str(row.get("project", "")).strip()
                for row in datasets
                if str(row.get("project", "")).strip()
            }
        )

        data_types = sorted(
            {
                str(row.get("data_type", "")).strip()
                for row in datasets
                if str(row.get("data_type", "")).strip()
            }
        )

        return {
            "collection_id": "bioqure-public-tcga",
            "name": "BIOQURE Public Dataset Pool",
            "count": len(datasets),
            "projects": projects,
            "data_types": data_types,
            "manifest_path": str(self.manifest_path),
            "public_root": str(self.public_root),
        }


__all__ = [
    "BIOQUREPublicDatasetRepository",
    "MANIFEST_FILENAME",
    "EXPRESSION_FILENAME",
    "METADATA_FILENAME",
]
