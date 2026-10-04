"""Locked single-sample BioQure inference primitives."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path
import threading
import time
import uuid

import dill
import joblib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "configs/final_model_lock.json"
FEATURE_NAMES = (
    "FABP4", "LEP", "COL10A1", "CHRDL1", "SCARA5", "SAA1", "SFRP1", "LPL"
)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_SUFFIX = ".rna_seq.augmented_star_gene_counts.tsv"
SUMMARY_ROWS = {"N_unmapped", "N_multimapping", "N_noFeature", "N_ambiguous"}


class InferenceError(ValueError):
    """A safe, user-facing inference validation error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_numeric(value: str, gene_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise InferenceError(f"TPM for {gene_name} is not numeric.") from error
    if not math.isfinite(number) or number < 0:
        raise InferenceError(f"TPM for {gene_name} must be finite and non-negative.")
    return number


def _parse_star_counts(content: bytes | str) -> tuple[dict[str, float], int]:
    """Extract locked biomarkers and count non-summary gene rows."""
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    lines = text.splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "gene_id" in line.split("\t")
            and "gene_name" in line.split("\t")
            and "tpm_unstranded" in line.split("\t")
        ),
        None,
    )
    if header_index is None:
        raise InferenceError(
            "Could not find a STAR-counts header with gene_name and tpm_unstranded."
        )

    reader = csv.DictReader(
        io.StringIO("\n".join(lines[header_index:])), delimiter="\t"
    )
    if (
        not reader.fieldnames
        or "gene_name" not in reader.fieldnames
        or "tpm_unstranded" not in reader.fieldnames
    ):
        raise InferenceError("STAR-counts file is missing required columns.")

    found: dict[str, float] = {}
    gene_count = 0
    for row in reader:
        gene_name = (row.get("gene_name") or "").strip()
        if not gene_name or gene_name in SUMMARY_ROWS:
            continue
        gene_count += 1
        if gene_name not in FEATURE_NAMES:
            continue
        if gene_name in found:
            raise InferenceError(f"Duplicate biomarker symbol: {gene_name}.")
        found[gene_name] = _parse_numeric(row.get("tpm_unstranded"), gene_name)

    missing = [gene for gene in FEATURE_NAMES if gene not in found]
    if missing:
        raise InferenceError(f"Missing locked biomarkers: {', '.join(missing)}")
    return {gene: found[gene] for gene in FEATURE_NAMES}, gene_count


def parse_star_counts(content: bytes | str) -> dict[str, float]:
    """Extract exactly one non-summary row for each locked biomarker."""
    values, _ = _parse_star_counts(content)
    return values


def _class_name(value: int) -> str:
    return "Tumor" if int(value) == 1 else "Normal"


def _display_circuit_name(value: str) -> str:
    names = {
        "zz_feature_map": "ZZFeatureMap",
        "real_amplitudes": "RealAmplitudes",
    }
    return names.get(value, value)


class LockedInferenceEngine:
    def __init__(self, lock_path: Path = LOCK_PATH) -> None:
        self.lock_path = lock_path.resolve()
        self.lock = json.loads(self.lock_path.read_text(encoding="utf-8"))
        if list(self.lock["data"]["feature_names"]) != list(FEATURE_NAMES):
            raise RuntimeError(
                "Locked feature order is not the required eight-gene contract."
            )

        self.lock_hash = sha256_file(self.lock_path)
        runtime_manifest_path = ROOT / "runtime/config/runtime_model_manifest.json"
        self.runtime_manifest = (
            json.loads(runtime_manifest_path.read_text(encoding="utf-8"))
            if runtime_manifest_path.is_file()
            else None
        )
        self.prepared_dir = ROOT / self.lock["data"]["prepared_data_dir"]
        self.classical_scaler = self._load_hashed(
            self.lock["preprocessing_artifacts"][0]
        )
        self.quantum_scaler = self._load_hashed(
            self.lock["preprocessing_artifacts"][1]
        )

        primary = self.lock["models"]["overall_primary"]
        self.classical_model = self._load_hashed(
            {"path": primary["model_path"], "sha256": primary["model_sha256"]}
        )
        self.a_models = [
            self._load_hashed(item)
            for item in self.lock["models"]["primary_quantum"]["model_files"]
        ]
        self.e_models = [
            self._load_hashed(item)
            for item in self.lock["models"]["secondary_quantum"][
                "candidate_e_model_files"
            ]
        ]
        self.demo_samples = self._load_demo_pool()
        self.inference_lock = threading.RLock()

    def _load_hashed(self, artifact: dict):
        original_path = artifact.get("path", artifact.get("model_path"))
        expected_hash = artifact.get("sha256", artifact.get("model_sha256"))
        runtime_path = next(
            (
                item["path"]
                for item in (self.runtime_manifest or {}).get("artifacts", [])
                if item["original_path"] == original_path
            ),
            original_path,
        )
        path = (
            ROOT / "runtime" / runtime_path
            if runtime_path != original_path
            else ROOT / original_path
        )
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise RuntimeError(f"Locked artifact hash mismatch: {original_path}")
        if path.suffix == ".joblib":
            return joblib.load(path)
        with path.open("rb") as handle:
            return dill.load(handle)

    def _load_demo_pool(self) -> dict[str, dict]:
        path = ROOT / "public_dataset_pool/catalog.json"
        pool = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(pool, list):
            raise RuntimeError("Public demo catalog must be a top-level JSON array.")
        for item in pool:
            if not isinstance(item, dict):
                raise RuntimeError("Public demo catalog entries must be JSON objects.")
            if item.get("split") != "train":
                raise RuntimeError("Demo pool contains a non-training sample.")
            fixture = (
                ROOT
                / "public_dataset_pool/raw"
                / f"{item['demo_id']}{ALLOWED_SUFFIX}"
            )
            if not fixture.is_file() or not fixture.name.endswith(ALLOWED_SUFFIX):
                raise RuntimeError(f"Invalid public demo sample: {item['demo_id']}")
            if sha256_file(fixture) != item.get("file_sha256"):
                raise RuntimeError(f"Public demo hash mismatch: {item['demo_id']}")
            item["fixture_path"] = fixture.relative_to(ROOT).as_posix()
            item["sample_id"] = item["demo_id"]
        return {item["demo_id"]: item for item in pool}

    def _quantum_backend_name(self) -> str:
        model = self.a_models[0]
        neural_network = getattr(model, "neural_network", None)
        if neural_network is None:
            neural_network = getattr(model, "_neural_network", None)
        sampler = getattr(neural_network, "sampler", None)
        if sampler is None:
            sampler = getattr(neural_network, "_sampler", None)
        return type(sampler).__name__ if sampler is not None else "Qiskit sampler"

    def _quantum_metadata(self) -> dict:
        primary = self.lock["models"]["primary_quantum"]
        secondary = self.lock["models"]["secondary_quantum"]
        backend = self._quantum_backend_name()
        execution_mode = (
            "local statevector simulation"
            if "statevector" in backend.lower()
            else "local Qiskit sampler"
        )
        return {
            "used": True,
            "fallback_used": False,
            "qubits": len(FEATURE_NAMES),
            "shots": primary["shots"],
            "backend": backend,
            "execution_mode": execution_mode,
            "optimizer": primary["optimizer"],
            "maxiter": primary["maxiter"],
            "primary_configuration": {
                "name": "Candidate A",
                "feature_map": _display_circuit_name(primary["feature_map"]),
                "feature_map_reps": primary["feature_map_reps"],
                "ansatz": _display_circuit_name(primary["ansatz"]),
                "ansatz_reps": primary["ansatz_reps"],
                "entanglement": primary["entanglement"],
                "seeds": primary["seeds"],
            },
            "secondary_configuration": {
                "name": "Candidate A/E balanced ensemble",
                "candidate_a": secondary["candidate_a_configuration"],
                "candidate_e": secondary["candidate_e_configuration"],
                "weight_candidate_a": secondary["weight_candidate_a"],
                "weight_candidate_e": secondary["weight_candidate_e"],
            },
        }

    def _benchmark_metadata(self) -> dict:
        primary = self.lock["models"]["primary_quantum"]
        secondary = self.lock["models"]["secondary_quantum"]
        secondary_metrics = secondary["validation_metrics"]
        quantum_robust = (
            secondary_metrics["sensitivity"] >= 0.80
            and secondary_metrics["specificity"] >= 0.70
        )
        return {
            "selected_model": "classical_logistic",
            "selected_model_label": self.lock["models"]["overall_primary"]["label"],
            "outcome": "classical",
            "checks": {
                "quantum_robust": quantum_robust,
                "quantum_improves": False,
                "quantum_robust_rule": (
                    "A/E validation sensitivity >= 0.80 and specificity >= 0.70"
                ),
                "quantum_improvement_reason": (
                    "The immutable lock keeps logistic regression as the best "
                    "validated deployment baseline."
                ),
            },
            "models": {
                "quantum_candidate_a_mean": {
                    "name": primary["label"],
                    **primary["validation_metrics"],
                },
                "quantum_ae_balanced": {
                    "name": secondary["label"],
                    **secondary_metrics,
                },
            },
            "calibration": {
                "metric": "Validation Brier score",
                "quantum_candidate_a": primary["validation_metrics"]["brier_score"],
                "quantum_ae_balanced": secondary_metrics["brier_score"],
                "classical_baseline": None,
                "classical_note": (
                    "Classical Brier score is not recorded in the immutable lock."
                ),
            },
        }

    def model_info(self) -> dict:
        return {
            "lock_sha256": self.lock_hash,
            "feature_count": len(FEATURE_NAMES),
            "feature_names": list(FEATURE_NAMES),
            "deployment_model": "classical_logistic",
            "endpoints": [
                self.lock["models"][key]["label"]
                for key in ("overall_primary", "primary_quantum", "secondary_quantum")
            ],
            "quantum": self._quantum_metadata(),
        }

    def demo_list(self) -> list[dict]:
        public_keys = (
            "demo_id", "display_name", "sample_type", "split", "file_sha256",
            "size_bytes", "biomarkers_available",
        )
        return [
            {key: item[key] for key in public_keys}
            for item in self.demo_samples.values()
        ]

    def infer(
        self,
        content: bytes,
        source_type: str,
        display_name: str,
        known_label: str | None = None,
    ) -> dict:
        started = time.perf_counter()
        extraction_started = time.perf_counter()
        raw_values, gene_count = _parse_star_counts(content)
        extraction_ms = (time.perf_counter() - extraction_started) * 1000

        preprocessing_started = time.perf_counter()
        raw = np.asarray(
            [raw_values[gene] for gene in FEATURE_NAMES], dtype=np.float64
        ).reshape(1, len(FEATURE_NAMES))
        log_values = np.log2(raw + 1.0)
        classical_scaled = self.classical_scaler.transform(log_values)
        quantum_angles = self.quantum_scaler.transform(log_values)
        preprocessing_ms = (time.perf_counter() - preprocessing_started) * 1000

        low = float(self.lock["data"]["quantum_angle_bounds"]["min"])
        high = float(self.lock["data"]["quantum_angle_bounds"]["max"])
        warnings = []
        if np.any(log_values < self.quantum_scaler.data_min_) or np.any(
            log_values > self.quantum_scaler.data_max_
        ):
            warnings.append(
                "One or more biomarkers are outside the fitted training range; "
                "the locked scaler was applied without refitting."
            )
        if (
            not np.all(np.isfinite(quantum_angles))
            or np.any(quantum_angles < low)
            or np.any(quantum_angles > high)
        ):
            warnings.append("Quantum angles are outside the locked zero-half-pi range.")

        classical_started = time.perf_counter()
        classical_probability = float(
            self.classical_model.predict_proba(classical_scaled)[0, 1]
        )
        classical_ms = (time.perf_counter() - classical_started) * 1000

        quantum_started = time.perf_counter()
        with self.inference_lock:
            a_seed = [
                float(model.predict_proba(quantum_angles)[0, 1])
                for model in self.a_models
            ]
            e_seed = [
                float(model.predict_proba(quantum_angles)[0, 1])
                for model in self.e_models
            ]
        quantum_ms = (time.perf_counter() - quantum_started) * 1000

        a_mean = float(np.mean(a_seed))
        a_median = float(np.median(a_seed))
        e_median = float(np.median(e_seed))
        predictions = {
            "classical_logistic": {
                "tumor_probability": classical_probability,
                "threshold": 0.50,
                "inference_ms": round(classical_ms, 2),
                "timing_scope": "endpoint",
            },
            "quantum_candidate_a_mean": {
                "tumor_probability": a_mean,
                "threshold": 0.33,
                "seed_probabilities": a_seed,
                "seed_standard_deviation": float(np.std(a_seed)),
                "seed_minimum": min(a_seed),
                "seed_maximum": max(a_seed),
                "inference_ms": round(quantum_ms, 2),
                "timing_scope": "shared_quantum_ensembles",
            },
            "quantum_ae_balanced": {
                "tumor_probability": float(0.55 * a_median + 0.45 * e_median),
                "threshold": 0.34,
                "inference_ms": round(quantum_ms, 2),
                "timing_scope": "shared_quantum_ensembles",
            },
        }
        for item in predictions.values():
            item["predicted_class"] = _class_name(
                int(item["tumor_probability"] >= item["threshold"])
            )
            if not 0 <= item["tumor_probability"] <= 1 or not math.isfinite(
                item["tumor_probability"]
            ):
                raise RuntimeError("Model produced a non-finite probability.")

        classes = [item["predicted_class"] for item in predictions.values()]
        total_ms = (time.perf_counter() - started) * 1000
        runtime = {
            "extraction_time_ms": round(extraction_ms, 2),
            "preprocessing_time_ms": round(preprocessing_ms, 2),
            "classical_inference_time_ms": round(classical_ms, 2),
            "quantum_inference_time_ms": round(quantum_ms, 2),
            "inference_time_ms": round(classical_ms + quantum_ms, 2),
            "total_time_ms": round(total_ms, 2),
            "quantum_used": True,
            "fallback_used": False,
        }
        result = {
            "request_id": str(uuid.uuid4()),
            "source": {"type": source_type, "display_name": display_name},
            "model_lock": {
                "lock_sha256": self.lock_hash,
                "feature_count": len(FEATURE_NAMES),
            },
            "input": {
                "sample_count": 1,
                "gene_count": gene_count,
                "feature_count": len(FEATURE_NAMES),
                "selected_feature_count": len(FEATURE_NAMES),
                "missing_feature_count": 0,
                "source_file": display_name,
            },
            "preprocessing": {
                "transformation": "log2(TPM + 1)",
                "scaler": (
                    f"{type(self.classical_scaler).__name__} (classical); "
                    f"{type(self.quantum_scaler).__name__} [0, pi/2] (quantum)"
                ),
                "classical_scaler": type(self.classical_scaler).__name__,
                "quantum_scaler": type(self.quantum_scaler).__name__,
                "feature_count": len(FEATURE_NAMES),
                "selected_feature_count": len(FEATURE_NAMES),
                "missing_feature_count": 0,
                "feature_names": list(FEATURE_NAMES),
                "duration_ms": round(preprocessing_ms, 2),
            },
            "quantum": self._quantum_metadata(),
            "runtime": runtime,
            "benchmark": self._benchmark_metadata(),
            "biomarkers": [
                {
                    "gene_name": gene,
                    "raw_tpm": float(raw_values[gene]),
                    "log2_tpm_plus_1": float(log_values[0, index]),
                    "classical_scaled_value": float(classical_scaled[0, index]),
                    "quantum_angle": float(quantum_angles[0, index]),
                }
                for index, gene in enumerate(FEATURE_NAMES)
            ],
            "predictions": predictions,
            "deployment_prediction": {
                "model": "classical_logistic",
                **predictions["classical_logistic"],
            },
            "agreement": {
                "all_models_agree": len(set(classes)) == 1,
                "summary": (
                    "All locked endpoints agree."
                    if len(set(classes)) == 1
                    else "Locked endpoints disagree; review endpoint probabilities."
                ),
            },
            "warnings": warnings,
            "timing_ms": {
                "extraction": round(extraction_ms, 2),
                "preprocessing": round(preprocessing_ms, 2),
                "classical_inference": round(classical_ms, 2),
                "quantum_inference": round(quantum_ms, 2),
                "total": round(total_ms, 2),
            },
        }
        if known_label:
            result["source"]["known_research_label"] = known_label
        return result
