"""Build the deterministic, training-only public demo pool."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import random
import shutil

from inference_service.inference import parse_star_counts


ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "expression_matrix/biomarker_outputs/sample_splits.csv"
SOURCE_ROOT = ROOT / "metadata extraction/gdc_data"
POOL_ROOT = ROOT / "public_dataset_pool"
RAW_ROOT = POOL_ROOT / "raw"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_path(row: dict[str, str]) -> Path:
    matches = sorted((SOURCE_ROOT / row["file_id"]).glob("*.rna_seq.augmented_star_gene_counts.tsv"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one raw TSV for {row['file_id']}, found {len(matches)}")
    return matches[0]


def select_rows() -> list[dict[str, str]]:
    with SPLITS.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"file_id", "case_id", "sample_type", "split"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise RuntimeError(
                "Sample split manifest is missing columns: "
                + ", ".join(sorted(missing))
            )
        rows = [row for row in reader if row["split"] == "train"]
    rng = random.Random(42)
    selected: list[dict[str, str]] = []
    for sample_type, count in (("Primary Tumor", 8), ("Solid Tissue Normal", 7)):
        candidates = [row for row in rows if row["sample_type"] == sample_type]
        rng.shuffle(candidates)
        cases: set[str] = set()
        for row in candidates:
            if row["case_id"] in cases:
                continue
            if not source_path(row).is_file():
                continue
            selected.append(row)
            cases.add(row["case_id"])
            if sum(item["sample_type"] == sample_type for item in selected) == count:
                break
        if sum(item["sample_type"] == sample_type for item in selected) != count:
            raise RuntimeError(f"Could not select {count} {sample_type} training samples")
    return selected


def main() -> None:
    selected = select_rows()
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    catalog = []
    for index, row in enumerate(selected, start=1):
        demo_id = f"BRCA-DEMO-{index:03d}"
        destination = RAW_ROOT / f"{demo_id}.rna_seq.augmented_star_gene_counts.tsv"
        source = source_path(row)
        content = source.read_bytes()
        parse_star_counts(content)
        shutil.copyfile(source, destination)
        catalog.append({
            "demo_id": demo_id,
            "display_name": f"TCGA-BRCA Demo {index:03d}",
            "sample_type": row["sample_type"],
            "split": "train",
            "file_sha256": sha256_file(destination),
            "size_bytes": destination.stat().st_size,
            "biomarkers_available": True,
            "label_verified": True,
            "label_provenance": "gdc_sample_metadata+training_split_manifest",
            "source_file_id": row["file_id"],
            "source_case_id": row["case_id"],
            "selection_seed": 42,
        })
    (POOL_ROOT / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    (POOL_ROOT / "README.md").write_text(
        "# Public dataset pool\n\n"
        "This deterministic pool contains eight Primary Tumor and seven Solid Tissue Normal "
        "GDC STAR-counts files selected from the training split with seed 42. The API exposes "
        "anonymous demo IDs and resolves files server-side; it never sends these files to the browser.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
