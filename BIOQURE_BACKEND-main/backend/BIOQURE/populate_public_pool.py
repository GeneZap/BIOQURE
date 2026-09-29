"""
Populate the BIOQURE public TCGA/GDC dataset pool.

This is a local/admin utility. It is NOT a public API endpoint.

Purpose:
    GDC manifest
        +
    downloaded RNA-seq expression files
        +
    optional sample metadata
        ↓
    select 20–30 datasets
        ↓
    copy them into:
        data/datasets/public/
        ↓
    create:
        manifest.json
        BRCA_001/metadata.json
        BRCA_001/expression.tsv
        ...

The script does NOT:
    - train models
    - modify trained model artifacts
    - download files from GDC
    - run quantum inference
    - expose an HTTP upload endpoint

Run from the repository root, for example:

    python backend/bioqure/populate_public_pool.py \
        --manifest "C:/path/to/gdc_manifest.txt" \
        --data-root "C:/path/to/downloaded/gdc/files" \
        --metadata "C:/path/to/gdc_sample_metadata.csv" \
        --count 25

For an explicitly selected set of GDC file IDs:

    python backend/bioqure/populate_public_pool.py \
        --manifest "C:/path/to/gdc_manifest.txt" \
        --data-root "C:/path/to/downloaded/gdc/files" \
        --metadata "C:/path/to/gdc_sample_metadata.csv" \
        --dataset-ids "UUID1,UUID2,UUID3,..."

Use --dry-run before the real population.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dataset_pools.config import get_datasets_root

try:
    from .config import get_feature_names
    from .dataset_repository import BIOQUREPublicDatasetRepository
except ImportError:
    from bioqure.config import get_feature_names
    from bioqure.dataset_repository import BIOQUREPublicDatasetRepository


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PUBLIC_COUNT = 25

RNA_SEQ_SUFFIX = ".rna_seq.augmented_star_gene_counts.tsv"

GDC_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{12}$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ManifestEntry:
    file_id: str
    filename: str
    md5: str | None
    size_bytes: int | None
    state: str | None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate the BIOQURE public TCGA/GDC dataset pool."
    )

    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to the downloaded GDC manifest .txt file.",
    )

    parser.add_argument(
        "--data-root",
        required=True,
        help=(
            "Directory containing downloaded GDC expression files. "
            "The directory is searched recursively."
        ),
    )

    parser.add_argument(
        "--metadata",
        default="",
        help="Optional GDC sample metadata CSV.",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_PUBLIC_COUNT,
        help=f"Number of datasets to publish. Default: {DEFAULT_PUBLIC_COUNT}.",
    )

    parser.add_argument(
        "--dataset-ids",
        default="",
        help=(
            "Comma-separated GDC file UUIDs to publish explicitly. "
            "When supplied, --count is ignored."
        ),
    )

    parser.add_argument(
        "--output-root",
        default="",
        help=(
            "Override dataset root. Default uses GENEZAP_DATASETS_ROOT "
            "or data/datasets."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing BIOQURE dataset IDs.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show selected datasets without copying files.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# GDC manifest
# ---------------------------------------------------------------------------

def _normalized_header(value: str) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
    )


def _find_column(
    columns: dict[str, int],
    *names: str,
) -> int | None:
    for name in names:
        idx = columns.get(_normalized_header(name))
        if idx is not None:
            return idx
    return None


def read_gdc_manifest(
    manifest_path: Path,
) -> list[ManifestEntry]:
    """
    Read a normal GDC manifest:

        id    filename    md5    size    state
    """
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"GDC manifest not found: {manifest_path}"
        )

    text = manifest_path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )

    lines = [
        line
        for line in text.splitlines()
        if line.strip()
        and not line.lstrip().startswith("#")
    ]

    if not lines:
        raise ValueError(
            f"GDC manifest is empty: {manifest_path}"
        )

    delimiter = "\t"

    if "\t" not in lines[0] and "," in lines[0]:
        delimiter = ","

    rows = list(
        csv.reader(
            lines,
            delimiter=delimiter,
        )
    )

    if not rows:
        raise ValueError(
            "GDC manifest contains no rows."
        )

    headers = rows[0]

    columns = {
        _normalized_header(header): index
        for index, header in enumerate(headers)
    }

    id_idx = _find_column(
        columns,
        "id",
        "file_id",
        "file_uuid",
        "uuid",
    )

    filename_idx = _find_column(
        columns,
        "filename",
        "file_name",
        "file name",
    )

    md5_idx = _find_column(
        columns,
        "md5",
        "md5sum",
        "md5_checksum",
    )

    size_idx = _find_column(
        columns,
        "size",
        "size_bytes",
        "file_size",
    )

    state_idx = _find_column(
        columns,
        "state",
        "status",
    )

    if id_idx is None:
        raise ValueError(
            "Could not find GDC file ID column."
        )

    if filename_idx is None:
        raise ValueError(
            "Could not find GDC filename column."
        )

    entries: list[ManifestEntry] = []

    for row in rows[1:]:
        if len(row) <= max(
            id_idx,
            filename_idx,
        ):
            continue

        file_id = row[id_idx].strip()
        filename = row[filename_idx].strip()

        if not GDC_UUID_RE.fullmatch(file_id):
            continue

        if not filename:
            continue

        md5 = None

        if (
            md5_idx is not None
            and len(row) > md5_idx
        ):
            value = row[md5_idx].strip()
            md5 = value or None

        size_bytes = None

        if (
            size_idx is not None
            and len(row) > size_idx
        ):
            value = row[size_idx].strip()

            if value:
                try:
                    size_bytes = int(
                        float(value)
                    )
                except ValueError:
                    size_bytes = None

        state = None

        if (
            state_idx is not None
            and len(row) > state_idx
        ):
            value = row[state_idx].strip()
            state = value or None

        entries.append(
            ManifestEntry(
                file_id=file_id,
                filename=filename,
                md5=md5,
                size_bytes=size_bytes,
                state=state,
            )
        )

    if not entries:
        raise ValueError(
            "No valid GDC entries were found in the manifest."
        )

    return entries


# ---------------------------------------------------------------------------
# Optional metadata CSV
# ---------------------------------------------------------------------------

def read_metadata_csv(
    metadata_path: Path | None,
) -> dict[str, dict[str, Any]]:
    """
    Read metadata indexed by GDC file UUID.

    If the metadata CSV does not contain a file UUID column, it is not
    safe to guess associations, so an empty index is returned.
    """
    if metadata_path is None:
        return {}

    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"GDC metadata file not found: {metadata_path}"
        )

    with metadata_path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            return {}

        fields = [
            str(field).strip()
            for field in reader.fieldnames
            if field
        ]

        normalized = {
            _normalized_header(field): field
            for field in fields
        }

        id_field = None

        for candidate in (
            "file_id",
            "id",
            "file_uuid",
            "gdc_file_id",
            "file_id_uuid",
        ):
            if candidate in normalized:
                id_field = normalized[candidate]
                break

        if id_field is None:
            return {}

        indexed: dict[str, dict[str, Any]] = {}

        for raw in reader:
            row = {
                str(key).strip(): value
                for key, value in raw.items()
                if key is not None
            }

            file_id = str(
                row.get(id_field) or ""
            ).strip()

            if file_id:
                indexed[file_id.lower()] = row

        return indexed


# ---------------------------------------------------------------------------
# Downloaded-file discovery
# ---------------------------------------------------------------------------

def build_download_index(
    data_root: Path,
) -> dict[str, list[Path]]:
    """
    Find downloaded RNA-seq files and index them by GDC file UUID.
    """
    if not data_root.is_dir():
        raise NotADirectoryError(
            f"GDC data root is not a directory: {data_root}"
        )

    index: dict[str, list[Path]] = {}

    for path in sorted(
        data_root.rglob(
            f"*{RNA_SEQ_SUFFIX}"
        ),
        key=lambda p: str(p).lower(),
    ):
        matches = GDC_UUID_RE.findall(
            path.name
        )

        if not matches:
            continue

        file_id = matches[0].lower()

        index.setdefault(
            file_id,
            [],
        ).append(path)

    return index


def locate_expression_file(
    entry: ManifestEntry,
    download_index: dict[str, list[Path]],
    data_root: Path,
) -> Path | None:
    """
    Locate the downloaded file first by GDC UUID and then by exact filename.
    """
    candidates = download_index.get(
        entry.file_id.lower()
    ) or []

    if candidates:
        return candidates[0]

    exact_matches = list(
        data_root.rglob(entry.filename)
    )

    if exact_matches:
        return sorted(
            exact_matches,
            key=lambda p: str(p).lower(),
        )[0]

    return None


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def _metadata_value(
    row: dict[str, Any],
    *names: str,
) -> str:
    normalized = {
        _normalized_header(key): value
        for key, value in row.items()
    }

    for name in names:
        key = _normalized_header(name)

        value = normalized.get(key)

        if value is not None and str(value).strip():
            return str(value).strip()

    return ""


def make_bioqure_id(
    number: int,
) -> str:
    return f"BRCA_{number:03d}"


def calculate_sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def build_dataset_metadata(
    entry: ManifestEntry,
    local_path: Path,
    metadata_row: dict[str, Any] | None,
    feature_names: list[str],
) -> dict[str, Any]:
    """
    Build the metadata stored beside each public dataset.
    """
    metadata_row = metadata_row or {}

    case_id = _metadata_value(
        metadata_row,
        "case_id",
        "case",
        "case_uuid",
    )

    sample_id = _metadata_value(
        metadata_row,
        "sample_id",
        "sample",
        "sample_uuid",
        "submitter_id",
    )

    project = _metadata_value(
        metadata_row,
        "project",
        "project_id",
        "project_name",
    ) or "TCGA-BRCA"

    sample_type = _metadata_value(
        metadata_row,
        "sample_type",
        "sample_type_id",
    )

    tissue_type = _metadata_value(
        metadata_row,
        "tissue_type",
        "tissue_source_site",
        "tissue",
    )

    access = _metadata_value(
        metadata_row,
        "access",
        "access_level",
        "data_access",
    ) or "open"

    return {
        "project": project,
        "data_type": "RNA-seq gene expression",
        "access": access,
        "description": (
            "Curated TCGA-BRCA RNA-seq expression sample "
            "prepared for BIOQURE research inference."
        ),

        # Original GDC identity.
        "gdc_file_id": entry.file_id,
        "case_id": case_id,
        "sample_id": sample_id,

        # Source file information.
        "original_filename": entry.filename,
        "download_filename": entry.filename,
        "manifest_md5": entry.md5,
        "manifest_size_bytes": entry.size_bytes,
        "local_sha256": calculate_sha256(
            local_path
        ),

        # Model input contract.
        "feature_count": len(feature_names),
        "feature_names": list(feature_names),

        # Optional metadata.
        "sample_type": sample_type or None,
        "tissue_type": tissue_type or None,

        # GDC manifest state.
        "source_gdc_state": entry.state,
    }


# ---------------------------------------------------------------------------
# Dataset selection
# ---------------------------------------------------------------------------

def parse_explicit_ids(
    value: str,
) -> list[str]:
    ids: list[str] = []

    for item in str(value or "").split(","):
        item = item.strip().lower()

        if item and item not in ids:
            ids.append(item)

    return ids


def select_entries(
    entries: list[ManifestEntry],
    download_index: dict[str, list[Path]],
    data_root: Path,
    count: int,
    explicit_ids: list[str],
) -> list[tuple[ManifestEntry, Path]]:
    """
    Select datasets deterministically.

    With --dataset-ids:
        publish exactly those IDs.

    Without --dataset-ids:
        publish the first `count` released RNA-seq files that exist locally.
    """
    entries_by_id = {
        entry.file_id.lower(): entry
        for entry in entries
    }

    selected: list[
        tuple[ManifestEntry, Path]
    ] = []

    # Explicit selection.
    if explicit_ids:
        missing: list[str] = []

        for file_id in explicit_ids:
            entry = entries_by_id.get(file_id)

            if entry is None:
                missing.append(
                    f"{file_id} (not in manifest)"
                )
                continue

            path = locate_expression_file(
                entry,
                download_index,
                data_root,
            )

            if path is None:
                missing.append(
                    f"{file_id} (not downloaded)"
                )
                continue

            if not entry.filename.lower().endswith(
                RNA_SEQ_SUFFIX
            ):
                missing.append(
                    f"{file_id} (not RNA-seq STAR count file)"
                )
                continue

            selected.append(
                (entry, path)
            )

        if missing:
            raise RuntimeError(
                "Could not select requested GDC files:\n  - "
                + "\n  - ".join(missing)
            )

        return selected

    # Automatic selection.
    if count < 1:
        raise ValueError(
            "--count must be at least 1."
        )

    for entry in entries:
        if len(selected) >= count:
            break

        if entry.state:
            if entry.state.lower() != "released":
                continue

        if not entry.filename.lower().endswith(
            RNA_SEQ_SUFFIX
        ):
            continue

        path = locate_expression_file(
            entry,
            download_index,
            data_root,
        )

        if path is None:
            continue

        selected.append(
            (entry, path)
        )

    if len(selected) < count:
        raise RuntimeError(
            f"Only {len(selected)} matching downloaded RNA-seq files "
            f"were found, but {count} were requested."
        )

    return selected


# ---------------------------------------------------------------------------
# Population
# ---------------------------------------------------------------------------

def populate(
    args: argparse.Namespace,
) -> int:
    manifest_path = Path(
        args.manifest
    ).expanduser().resolve()

    data_root = Path(
        args.data_root
    ).expanduser().resolve()

    metadata_path = (
        Path(args.metadata)
        .expanduser()
        .resolve()
        if args.metadata
        else None
    )

    entries = read_gdc_manifest(
        manifest_path
    )

    metadata_index = read_metadata_csv(
        metadata_path
    )

    download_index = build_download_index(
        data_root
    )

    explicit_ids = parse_explicit_ids(
        args.dataset_ids
    )

    selected = select_entries(
        entries,
        download_index,
        data_root,
        args.count,
        explicit_ids,
    )

    # This comes from the actual training/preparation configuration.
    feature_names = get_feature_names()

    if args.output_root:
        output_root = Path(
            args.output_root
        ).expanduser().resolve()
    else:
        output_root = get_datasets_root()

    repository = BIOQUREPublicDatasetRepository(
        root=output_root
    )

    print("")
    print("=" * 70)
    print("BIOQURE PUBLIC DATASET POOL")
    print("=" * 70)
    print(f"Manifest       : {manifest_path}")
    print(f"Data root      : {data_root}")
    print(f"Output root    : {repository.public_root}")
    print(f"Selected count : {len(selected)}")
    print(
        f"Biomarkers     : {', '.join(feature_names)}"
    )
    print("=" * 70)
    print("")

    for number, (
        entry,
        local_path,
    ) in enumerate(
        selected,
        start=1,
    ):
        dataset_id = make_bioqure_id(
            number
        )

        metadata_row = (
            metadata_index.get(
                entry.file_id.lower()
            )
            or metadata_index.get(
                entry.file_id
            )
        )

        metadata = build_dataset_metadata(
            entry,
            local_path,
            metadata_row,
            feature_names,
        )

        print(
            f"[{number:02d}] "
            f"{dataset_id} "
            f"<- {entry.file_id}"
        )

        print(
            f"      file: {local_path}"
        )

        if metadata.get("sample_id"):
            print(
                f"      sample: {metadata['sample_id']}"
            )

        if args.dry_run:
            continue

        repository.add_public_dataset(
            dataset_id=dataset_id,
            expression_bytes=local_path.read_bytes(),
            metadata=metadata,
            expression_filename="expression.tsv",
            overwrite=args.overwrite,
        )

    print("")

    if args.dry_run:
        print(
            "DRY RUN COMPLETE — no datasets were copied."
        )
    else:
        summary = repository.public_catalog_summary()

        print(
            "PUBLIC POOL CREATED SUCCESSFULLY"
        )
        print(
            f"Dataset count : {summary['count']}"
        )
        print(
            f"Manifest      : {summary['manifest_path']}"
        )
        print(
            f"Public root   : {summary['public_root']}"
        )

    print("")

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    try:
        return populate(args)

    except Exception as exc:  # noqa: BLE001
        print("")
        print(
            "BIOQURE public-pool population failed:"
        )
        print(
            f"  {exc}"
        )
        print("")
        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )