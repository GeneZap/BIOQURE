"""Copy only locked inference artifacts into the production runtime bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "configs/final_model_lock.json"
RUNTIME = ROOT / "runtime"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main() -> None:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    artifacts = [
        ("model_artifacts/classical/logistic_regression.joblib", lock["models"]["overall_primary"]),
        *[(f"model_artifacts/candidate_a/seed-{item['path'].split('seed')[-1].split('/')[0]}.dill", item) for item in lock["models"]["primary_quantum"]["model_files"]],
        *[(f"model_artifacts/candidate_e/seed-{item['path'].split('seed')[-1].split('/')[0]}.dill", item) for item in lock["models"]["secondary_quantum"]["candidate_e_model_files"]],
        ("model_artifacts/scalers/classical_scaler.joblib", lock["preprocessing_artifacts"][0]),
        ("model_artifacts/scalers/quantum_scaler.joblib", lock["preprocessing_artifacts"][1]),
        ("config/preparation_config.json", lock["preprocessing_artifacts"][2]),
    ]
    manifest_artifacts = []
    for relative_destination, artifact in artifacts:
        original_path = artifact.get("path", artifact.get("model_path"))
        original_hash = artifact.get("sha256", artifact.get("model_sha256"))
        source = ROOT / original_path
        destination = RUNTIME / relative_destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        copied_hash = digest(destination)
        if copied_hash != original_hash:
            raise RuntimeError(f"Copied artifact hash mismatch: {relative_destination}")
        manifest_artifacts.append({"path": relative_destination.replace("\\", "/"), "original_path": original_path, "original_sha256": original_hash, "copied_sha256": copied_hash})
    manifest = {"reference_lock": "../configs/final_model_lock.json", "feature_order": lock["data"]["feature_names"], "thresholds": {"classical": 0.50, "candidate_a": 0.33, "combined": 0.34}, "ensemble_weights": {"candidate_a": 0.55, "candidate_e": 0.45}, "artifacts": manifest_artifacts, "package_versions": lock["package_versions"]}
    (RUNTIME / "config/runtime_model_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (RUNTIME / "README.md").write_text("# BIOQURE runtime bundle\n\nThis bundle contains only hash-verified locked inference artifacts. The immutable research lock remains the source of truth.\n", encoding="utf-8")


if __name__ == "__main__":
    main()