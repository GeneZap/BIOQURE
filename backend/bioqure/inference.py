"""
BIOQURE trained-model inference.

This module performs inference only. It does not:
- fit models
- select new biomarkers
- fit scalers
- download data
- fabricate fallback predictions

It consumes the model-ready arrays produced by bioqure.preprocessing.py and
loads the trained artifacts created by train_hybrid_models.py.

Current training artifacts supported:
    logistic_regression.joblib
    rbf_svm.joblib
    vqc.model
    vqc_probability_calibrator.joblib   (optional)
    metrics.json                        (optional but strongly recommended)

The VQC was trained with Qiskit's VQC and persisted to disk. Current
Qiskit Machine Learning releases support loading serialized VQC models with
VQC.from_dill(); older releases expose VQC.load() as a compatibility alias.
"""

from __future__ import annotations

import json
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from .config import (
    get_feature_names,
    get_logistic_regression_model_path,
    get_rbf_svm_model_path,
    get_training_metrics_path,
    get_vqc_calibrator_path,
    get_vqc_model_path,
    require_file,
)
from .preprocessing import PreparedBIOQURESample, feature_vector_summary


# ---------------------------------------------------------------------------
# Small numerical helpers
# ---------------------------------------------------------------------------

def _as_one_row(values: np.ndarray | list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)

    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    if arr.ndim != 2 or arr.shape[0] != 1:
        raise ValueError(f"Expected one sample, got array with shape {arr.shape}")

    if not np.all(np.isfinite(arr)):
        raise ValueError("Model input contains non-finite values.")

    return arr


def _positive_probability(probabilities: Any) -> float:
    """
    Convert a classifier probability output into P(class=1).

    Expected binary output:
        [[p0, p1]]

    We also support a one-dimensional binary probability vector:
        [p0, p1]

    A scalar is accepted as an already-computed positive-class probability.
    """
    values = np.asarray(probabilities, dtype=float)

    if values.size == 0:
        raise ValueError("Model returned an empty probability array.")

    if values.ndim == 0:
        p = float(values)
    elif values.ndim == 1:
        if values.size == 1:
            p = float(values[0])
        elif values.size == 2:
            p = float(values[1])
        else:
            raise ValueError(
                f"Unexpected probability shape for binary classifier: {values.shape}"
            )
    elif values.ndim == 2:
        if values.shape == (1, 1):
            p = float(values[0, 0])
        elif values.shape[0] == 1 and values.shape[1] == 2:
            p = float(values[0, 1])
        else:
            raise ValueError(
                f"Unexpected probability shape for one-sample binary inference: "
                f"{values.shape}"
            )
    else:
        raise ValueError(
            f"Unexpected probability output shape: {values.shape}"
        )

    if not np.isfinite(p):
        raise ValueError("Model returned a non-finite probability.")

    # Probability APIs should already be in [0, 1], but tolerate tiny
    # floating-point excursions.
    return float(np.clip(p, 0.0, 1.0))


def _positive_prediction(prediction: Any) -> int:
    """
    Normalize common sklearn/Qiskit binary prediction outputs to 0/1.
    """
    values = np.asarray(prediction)

    if values.size == 0:
        raise ValueError("Model returned an empty prediction.")

    # Most sklearn classifiers return shape (1,), while VQC can return
    # shape (1,) or a one-hot row depending on configuration/version.
    if values.ndim == 0:
        raw = values.item()
    elif values.ndim == 1:
        if values.size == 1:
            raw = values[0]
        elif values.size == 2:
            # One-hot encoding: [1,0] => 0, [0,1] => 1.
            raw = int(np.argmax(values))
        else:
            raise ValueError(
                f"Unexpected binary prediction shape: {values.shape}"
            )
    elif values.ndim == 2 and values.shape == (1, 1):
        raw = values[0, 0]
    elif values.ndim == 2 and values.shape == (1, 2):
        raw = int(np.argmax(values[0]))
    else:
        raise ValueError(
            f"Unexpected binary prediction shape: {values.shape}"
        )

    # Qiskit/sklearn normally return numeric 0/1 labels for this training
    # pipeline. We also accept common string representations.
    if isinstance(raw, str):
        label = raw.strip().lower()
        if label in {"1", "1.0", "tumor", "tumour", "positive", "pos"}:
            return 1
        if label in {"0", "0.0", "normal", "negative", "neg"}:
            return 0
        raise ValueError(f"Unsupported model prediction label: {raw!r}")

    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unsupported model prediction: {raw!r}") from exc

    if not np.isfinite(number):
        raise ValueError("Model returned a non-finite prediction.")

    return 1 if number >= 0.5 else 0


def _label_from_prediction(value: int) -> str:
    return "Tumor" if int(value) == 1 else "Normal"


def _confidence_from_probability(p_tumor: float) -> float:
    """
    Distance from 0.5 expressed as a percentage.

    This is a decision confidence display, not a calibrated uncertainty
    estimate. Calibrated VQC probability is returned separately.
    """
    p = float(np.clip(p_tumor, 0.0, 1.0))
    return float(round(max(p, 1.0 - p) * 100.0, 2))


# ---------------------------------------------------------------------------
# Trained artifact loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_logistic_model() -> Any:
    path = require_file(
        get_logistic_regression_model_path(),
        "logistic regression model",
    )
    return joblib.load(path)


@lru_cache(maxsize=1)
def load_rbf_svm_model() -> Any:
    path = require_file(
        get_rbf_svm_model_path(),
        "RBF-SVM model",
    )
    return joblib.load(path)


@lru_cache(maxsize=1)
def load_vqc_model() -> Any:
    """
    Load the saved Qiskit VQC.

    Qiskit Machine Learning 0.9.x uses VQC.from_dill() as the canonical
    loader, while older versions expose VQC.load(). We support both without
    requiring the backend process to import Qiskit at startup.
    """
    path = require_file(
        get_vqc_model_path(),
        "VQC model",
    )

    try:
        from qiskit_machine_learning.algorithms import VQC
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Qiskit Machine Learning could not be imported while loading the "
            f"BIOQURE VQC model. Check qiskit-machine-learning installation "
            f"and version compatibility with {path}."
        ) from exc

    loader = getattr(VQC, "from_dill", None)

    try:
        if callable(loader):
            return loader(str(path))

        legacy_loader = getattr(VQC, "load", None)
        if callable(legacy_loader):
            return legacy_loader(str(path))

    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Could not load BIOQURE VQC artifact: {path}. "
            f"Original error: {exc}"
        ) from exc

    raise RuntimeError(
        "Installed Qiskit Machine Learning VQC class exposes neither "
        "from_dill() nor load()."
    )


@lru_cache(maxsize=1)
def load_vqc_calibrator() -> Any | None:
    """
    Load the validation-fitted VQC probability calibrator when present.

    The training script only creates this artifact when --evaluate-test is
    used. Therefore its absence is allowed; in that case raw VQC probability
    is retained and marked as uncalibrated.
    """
    path = get_vqc_calibrator_path()

    if not path.is_file():
        return None

    return joblib.load(path)


@lru_cache(maxsize=1)
def load_training_metrics() -> dict[str, Any]:
    path = get_training_metrics_path()

    if not path.is_file():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Model inference
# ---------------------------------------------------------------------------

def infer_logistic_regression(
    classical_features: np.ndarray,
) -> dict[str, Any]:
    model = load_logistic_model()
    X = _as_one_row(classical_features)

    if not hasattr(model, "predict"):
        raise TypeError("Saved logistic regression artifact has no predict().")

    prediction = _positive_prediction(model.predict(X))

    if not hasattr(model, "predict_proba"):
        raise TypeError(
            "Saved logistic regression model does not expose predict_proba()."
        )

    probability = _positive_probability(model.predict_proba(X))

    return {
        "model": "logistic_regression",
        "display_name": "Logistic Regression",
        "prediction": prediction,
        "label": _label_from_prediction(prediction),
        "tumor_probability": round(probability, 6),
        "confidence_percent": _confidence_from_probability(probability),
    }


def infer_rbf_svm(
    classical_features: np.ndarray,
) -> dict[str, Any]:
    model = load_rbf_svm_model()
    X = _as_one_row(classical_features)

    if not hasattr(model, "predict"):
        raise TypeError("Saved RBF-SVM artifact has no predict().")

    prediction = _positive_prediction(model.predict(X))

    # The training script creates SVC without probability=True. Therefore
    # decision_function is the available score. We expose it separately and
    # derive a display probability with a monotonic logistic transform only
    # when needed for the UI. This is NOT a calibrated probability.
    decision_score: float | None = None
    display_probability: float | None = None

    if hasattr(model, "decision_function"):
        raw_score = np.asarray(model.decision_function(X), dtype=float).reshape(-1)

        if raw_score.size:
            decision_score = float(raw_score[0])

            # Logistic squashing is only a visualization-scale probability.
            # It must not be presented as calibrated.
            z = np.clip(decision_score, -60.0, 60.0)
            display_probability = float(1.0 / (1.0 + np.exp(-z)))

    return {
        "model": "rbf_svm",
        "display_name": "RBF-SVM",
        "prediction": prediction,
        "label": _label_from_prediction(prediction),
        "decision_score": (
            round(decision_score, 6)
            if decision_score is not None
            else None
        ),
        "display_probability": (
            round(display_probability, 6)
            if display_probability is not None
            else None
        ),
        "probability_calibrated": False,
        "confidence_percent": (
            _confidence_from_probability(display_probability)
            if display_probability is not None
            else None
        ),
    }


# A VQC sampler/model can be shared by several requests. Prediction is
# protected so concurrent requests do not accidentally mutate a shared
# primitive or model object in an unsupported way.
_VQC_LOCK = threading.RLock()


def _vqc_predict_probability(
    model: Any,
    X: np.ndarray,
) -> tuple[int, float]:
    if not hasattr(model, "predict"):
        raise TypeError("Saved VQC artifact has no predict().")

    if not hasattr(model, "predict_proba"):
        raise TypeError(
            "Saved VQC artifact has no predict_proba(). "
            "The stored VQC must support probability inference."
        )

    with _VQC_LOCK:
        raw_prediction = model.predict(X)
        raw_probability = model.predict_proba(X)

    prediction = _positive_prediction(raw_prediction)
    probability = _positive_probability(raw_probability)

    return prediction, probability


def infer_vqc(
    quantum_features: np.ndarray,
) -> dict[str, Any]:
    model = load_vqc_model()
    X = _as_one_row(quantum_features)

    expected = getattr(model, "num_qubits", None)
    if expected is not None and int(expected) != X.shape[1]:
        raise ValueError(
            f"Saved VQC expects {expected} inputs/qubits, but preprocessing "
            f"produced {X.shape[1]} features."
        )

    raw_prediction, raw_probability = _vqc_predict_probability(model, X)

    calibrator = load_vqc_calibrator()
    calibrated_probability: float | None = None

    if calibrator is not None:
        calibrated_probability = _positive_probability(
            calibrator.predict_proba(
                np.asarray([[raw_probability]], dtype=np.float64)
            )
        )

    effective_probability = (
        calibrated_probability
        if calibrated_probability is not None
        else raw_probability
    )

    effective_prediction = int(effective_probability >= 0.5)

    # Some VQC configurations can return a prediction thresholded differently
    # from the calibrated probability. We report both raw prediction and the
    # probability-derived result so the distinction is visible.
    return {
        "model": "vqc",
        "display_name": "Variational Quantum Classifier",
        "raw_prediction": int(raw_prediction),
        "raw_label": _label_from_prediction(raw_prediction),
        "raw_probability": round(raw_probability, 6),
        "calibrated_probability": (
            round(calibrated_probability, 6)
            if calibrated_probability is not None
            else None
        ),
        "prediction": effective_prediction,
        "label": _label_from_prediction(effective_prediction),
        "confidence_percent": _confidence_from_probability(
            effective_probability
        ),
        "probability_calibrated": calibrated_probability is not None,
        "calibrator_available": calibrator is not None,
    }


# ---------------------------------------------------------------------------
# Training metadata
# ---------------------------------------------------------------------------

def _validation_metrics() -> dict[str, Any]:
    metrics = load_training_metrics()
    raw = metrics.get("validation")
    return raw if isinstance(raw, dict) else {}


def _test_metrics() -> dict[str, Any]:
    metrics = load_training_metrics()
    raw = metrics.get("test")
    return raw if isinstance(raw, dict) else {}


def _model_metrics(name: str) -> dict[str, Any]:
    validation = _validation_metrics()
    row = validation.get(name)
    return dict(row) if isinstance(row, dict) else {}


def training_summary() -> dict[str, Any]:
    """
    Return non-secret training metadata suitable for the frontend.
    """
    metrics = load_training_metrics()

    configuration = metrics.get("configuration")
    if not isinstance(configuration, dict):
        configuration = {}

    return {
        "feature_names": get_feature_names(),
        "feature_count": len(get_feature_names()),
        "configuration": configuration,
        "validation": _validation_metrics(),
        "test_available": bool(_test_metrics()),
        "test_evaluated": bool(metrics.get("configuration", {}).get("test_evaluated")),
        "artifacts": {
            "logistic_regression": get_logistic_regression_model_path().is_file(),
            "rbf_svm": get_rbf_svm_model_path().is_file(),
            "vqc": get_vqc_model_path().is_file(),
            "vqc_calibrator": get_vqc_calibrator_path().is_file(),
        },
    }


# ---------------------------------------------------------------------------
# Model selection / comparison
# ---------------------------------------------------------------------------

def _validated_classical_candidates() -> list[tuple[str, dict[str, Any]]]:
    """
    Return trained classical models with validation metrics.

    We only select among models that both:
    - exist on disk, and
    - have a validation balanced-accuracy record.

    Current training script trains Logistic Regression and RBF-SVM.
    """
    candidates: list[tuple[str, dict[str, Any]]] = []

    for name in ("logistic_regression", "rbf_svm"):
        path = (
            get_logistic_regression_model_path()
            if name == "logistic_regression"
            else get_rbf_svm_model_path()
        )

        metrics = _model_metrics(name)

        if path.is_file() and "balanced_accuracy" in metrics:
            candidates.append((name, metrics))

    return candidates


def select_validated_model() -> dict[str, Any]:
    """
    Select the deployed prediction path from validation-only metrics.

    This implements the project rule:
        use VQC when it is at least competitive with the best validated
        classical baseline; otherwise use the validated classical baseline.

    This function never examines held-out test performance for selection.
    """
    classical_candidates = _validated_classical_candidates()

    if not classical_candidates:
        raise RuntimeError(
            "No validated classical model is available for BIOQURE model "
            "selection."
        )

    best_classical_name, best_classical_metrics = max(
        classical_candidates,
        key=lambda item: float(item[1]["balanced_accuracy"]),
    )

    vqc_metrics = _model_metrics("vqc")
    vqc_path_exists = get_vqc_model_path().is_file()
    vqc_validation_score = vqc_metrics.get("balanced_accuracy")

    if vqc_path_exists and vqc_validation_score is not None:
        classical_score = float(best_classical_metrics["balanced_accuracy"])
        quantum_score = float(vqc_validation_score)

        if quantum_score >= classical_score:
            selected = "vqc"
            reason = (
                "VQC matched or exceeded the best classical validation "
                "balanced accuracy."
            )
        else:
            selected = best_classical_name
            reason = (
                "The best validated classical baseline exceeded the VQC "
                "validation balanced accuracy."
            )
    else:
        selected = best_classical_name
        reason = (
            "VQC validation metrics or artifact are unavailable; using the "
            "validated classical baseline."
        )

    return {
        "selected_model": selected,
        "selected_display_name": (
            "Variational Quantum Classifier"
            if selected == "vqc"
            else (
                "Logistic Regression"
                if selected == "logistic_regression"
                else "RBF-SVM"
            )
        ),
        "reason": reason,
        "best_classical_model": best_classical_name,
        "best_classical_validation_balanced_accuracy": float(
            best_classical_metrics["balanced_accuracy"]
        ),
        "vqc_validation_balanced_accuracy": (
            float(vqc_validation_score)
            if vqc_validation_score is not None
            else None
        ),
        "selection_uses_test_data": False,
    }


# ---------------------------------------------------------------------------
# Complete sample inference
# ---------------------------------------------------------------------------

def infer_prepared_sample(
    prepared: PreparedBIOQURESample,
) -> dict[str, Any]:
    """
    Run all available trained models on one prepared BIOQURE sample.
    """
    expected_features = get_feature_names()

    if list(prepared.feature_names) != expected_features:
        raise ValueError(
            "Prepared feature order does not match the training configuration. "
            f"Expected {expected_features}, got {prepared.feature_names}"
        )

    classical = infer_logistic_regression(prepared.classical_features)
    svm = infer_rbf_svm(prepared.classical_features)
    quantum = infer_vqc(prepared.quantum_features)

    selection = select_validated_model()

    model_outputs = {
        "logistic_regression": classical,
        "rbf_svm": svm,
        "vqc": quantum,
    }

    selected_output = model_outputs[selection["selected_model"]]

    return {
        "status": "complete",
        "selected_model": selection["selected_model"],
        "selected_model_display_name": selection["selected_display_name"],
        "selection": selection,
        "prediction": int(selected_output["prediction"]),
        "label": str(selected_output["label"]),
        "tumor_probability": (
            float(selected_output["tumor_probability"])
            if "tumor_probability" in selected_output
            else float(
                selected_output.get("calibrated_probability")
                or selected_output.get("raw_probability")
                or 0.0
            )
        ),
        "confidence_percent": float(
            selected_output.get("confidence_percent") or 0.0
        ),
        "models": model_outputs,
        "biomarkers": feature_vector_summary(prepared),
        "training": training_summary(),
    }


# ---------------------------------------------------------------------------
# Public helpers for the API layer
# ---------------------------------------------------------------------------

def analyze_prepared_sample(
    prepared: PreparedBIOQURESample,
) -> dict[str, Any]:
    """
    Public inference entry point for a sample that has already gone through
    GDC preprocessing.
    """
    return infer_prepared_sample(prepared)


def clear_model_caches() -> None:
    """
    Clear cached model instances.

    Useful for local development or when model artifacts are replaced without
    restarting the API process.
    """
    load_logistic_model.cache_clear()
    load_rbf_svm_model.cache_clear()
    load_vqc_model.cache_clear()
    load_vqc_calibrator.cache_clear()
    load_training_metrics.cache_clear()


__all__ = [
    "load_logistic_model",
    "load_rbf_svm_model",
    "load_vqc_model",
    "load_vqc_calibrator",
    "load_training_metrics",
    "training_summary",
    "select_validated_model",
    "infer_logistic_regression",
    "infer_rbf_svm",
    "infer_vqc",
    "infer_prepared_sample",
    "analyze_prepared_sample",
    "clear_model_caches",
]
