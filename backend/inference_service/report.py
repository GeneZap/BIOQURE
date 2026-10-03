"""Frontend report sections derived from a locked inference result.

Every value is taken from the locked models, the immutable model lock, or the
current request. Nothing here refits, recalibrates, or changes a threshold.
"""

from __future__ import annotations

import math

import numpy as np


PRIMARY_MODEL_NAME = "Logistic regression (locked primary)"
PRIMARY_MODEL_KEY = "logistic_regression"
FEATURE_MAP_NAMES = {"zz_feature_map": "ZZFeatureMap"}
ANSATZ_NAMES = {"real_amplitudes": "RealAmplitudes"}
METRIC_SOURCE = "Validation split recorded in the immutable model lock; the held-out test split has not been evaluated."


def _validation_summary(metrics: dict | None) -> dict:
    if not metrics:
        return {}
    tp, fp, fn = metrics.get("tp"), metrics.get("fp"), metrics.get("fn")
    f1 = None
    if None not in (tp, fp, fn) and (2 * tp + fp + fn) > 0:
        f1 = 2 * tp / (2 * tp + fp + fn)
    return {
        "accuracy": metrics.get("accuracy"),
        "auc": metrics.get("roc_auc"),
        "pr_auc": metrics.get("pr_auc"),
        "f1": f1,
        "brier_score": metrics.get("brier_score"),
        "balanced_accuracy": metrics.get("balanced_accuracy"),
        "sensitivity": metrics.get("sensitivity"),
        "specificity": metrics.get("specificity"),
        "mcc": metrics.get("mcc"),
        "confusion_matrix": {key: metrics.get(key) for key in ("tn", "fp", "fn", "tp")},
    }


def _circuit_description(config: dict, key: str, names: dict, reps_key: str) -> str:
    name = names.get(config.get(key), config.get(key) or "Not recorded")
    reps = config.get(reps_key)
    return f"{name} (reps {reps})" if reps is not None else name


def biomarker_importance(coefficients: np.ndarray) -> list[dict]:
    """Relative |coefficient| of the locked logistic model on standardized inputs."""
    weights = np.asarray(coefficients, dtype=np.float64).reshape(-1)
    largest = float(np.max(np.abs(weights))) or 1.0
    rows = []
    for weight in weights:
        tumor_leaning = weight > 0
        rows.append({
            "importance": abs(float(weight)) / largest,
            "logistic_coefficient": float(weight),
            "direction": "Tumor" if tumor_leaning else "Normal",
            "note": (
                "Higher standardized expression raises the locked logistic tumor-class score."
                if tumor_leaning
                else "Higher standardized expression lowers the locked logistic tumor-class score."
            ),
        })
    return rows


def build_report_sections(lock: dict, result: dict, genes_detected: int, quantum_timing_ms: dict) -> dict:
    predictions = result["predictions"]
    classical = predictions["classical_logistic"]
    candidate_a = predictions["quantum_candidate_a_mean"]
    balanced = predictions["quantum_ae_balanced"]
    primary_quantum = lock["models"]["primary_quantum"]
    secondary_quantum = lock["models"]["secondary_quantum"]
    probability = classical["tumor_probability"]
    is_tumor = classical["predicted_class"] == "Tumor"

    prediction = {
        "label": classical["predicted_class"],
        "predicted_class": classical["predicted_class"],
        "tumor_probability": probability,
        "tumour_probability": probability,
        "probability": probability,
        "confidence": probability if is_tumor else 1.0 - probability,
        "threshold": classical["threshold"],
        "selected_model": PRIMARY_MODEL_NAME,
        "selected_model_key": PRIMARY_MODEL_KEY,
    }

    quantum_probability = candidate_a["tumor_probability"]
    quantum = {
        "used": True,
        "model": primary_quantum["label"],
        "simulator": "Qiskit StatevectorSampler",
        "feature_map": _circuit_description(primary_quantum, "feature_map", FEATURE_MAP_NAMES, "feature_map_reps"),
        "ansatz": f"{_circuit_description(primary_quantum, 'ansatz', ANSATZ_NAMES, 'ansatz_reps')}, {primary_quantum.get('entanglement', 'linear')} entanglement",
        "optimizer": primary_quantum.get("optimizer"),
        "shots": primary_quantum.get("shots"),
        "qubits": len(result["biomarkers"]),
        "encoding": "MinMax angle encoding to [0, pi/2] (scaler fitted on the training split)",
        "scaled_features": [row["quantum_angle"] for row in result["biomarkers"]],
        "angle_bounds": lock["data"]["quantum_angle_bounds"],
        "tumor_probability": quantum_probability,
        "probabilities": {"tumor": quantum_probability, "normal": 1.0 - quantum_probability},
        "predicted_class": candidate_a["predicted_class"],
        "threshold": candidate_a["threshold"],
        "seed_probabilities": candidate_a["seed_probabilities"],
        "seeds": primary_quantum.get("seeds"),
        "ensembles": {
            "quantum_candidate_a_mean": {"name": primary_quantum["label"], **{key: candidate_a[key] for key in ("tumor_probability", "threshold", "predicted_class")}},
            "quantum_ae_balanced": {"name": secondary_quantum["label"], **{key: balanced[key] for key in ("tumor_probability", "threshold", "predicted_class")}},
        },
    }

    benchmark = {
        "selected_model": PRIMARY_MODEL_NAME,
        "selected_model_key": PRIMARY_MODEL_KEY,
        "outcome": "classical",
        "best_classical_model": "Logistic regression",
        "metric_source": METRIC_SOURCE,
        "models": {
            "logistic_regression": {
                "name": "Logistic regression",
                "threshold": classical["threshold"],
                "predicted_class": classical["predicted_class"],
                "inference_ms": result["timing_ms"]["classical_inference"],
            },
            "quantum_candidate_a_mean": {
                "name": primary_quantum["label"],
                "threshold": candidate_a["threshold"],
                "predicted_class": candidate_a["predicted_class"],
                "inference_ms": quantum_timing_ms["candidate_a"],
                **_validation_summary(primary_quantum.get("validation_metrics")),
            },
            "quantum_ae_balanced": {
                "name": secondary_quantum["label"],
                "threshold": balanced["threshold"],
                "predicted_class": balanced["predicted_class"],
                "inference_ms": round(quantum_timing_ms["candidate_a"] + quantum_timing_ms["candidate_e"], 2),
                **_validation_summary(secondary_quantum.get("validation_metrics")),
            },
        },
        "calibration": {
            "metric": "Validation Brier score",
            "quantum": (primary_quantum.get("validation_metrics") or {}).get("brier_score"),
        },
    }

    input_metrics = {
        "samples": 1,
        "genes_detected": genes_detected,
        "biomarkers_used": len(result["biomarkers"]),
        "biomarker_values_used": {row["gene_name"]: row["raw_tpm"] for row in result["biomarkers"]},
        "value_type": "tpm_unstranded",
    }

    sections = {
        "prediction": prediction,
        "selected_model": PRIMARY_MODEL_NAME,
        "selected_model_key": PRIMARY_MODEL_KEY,
        "quantum_used": True,
        "classical_models": {
            "logistic_regression": {
                "name": "Logistic regression",
                "tumor_probability": probability,
                "threshold": classical["threshold"],
                "predicted_class": classical["predicted_class"],
            }
        },
        "quantum": quantum,
        "benchmark": benchmark,
        "input_metrics": input_metrics,
    }
    for value in (prediction["probability"], quantum_probability):
        if not math.isfinite(value):
            raise RuntimeError("Report contains a non-finite probability.")
    return sections
