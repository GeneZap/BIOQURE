"""
BIOQURE configuration and model-artifact paths.

This module does not perform model inference.
It only provides:
- BIOQURE artifact locations
- prepared-data configuration loading
- authoritative feature-name loading
- model/scaler artifact paths
- environment-variable overrides for deployment

Environment variables:
    BIOQURE_MODEL_ROOT
        Directory containing trained inference artifacts.

    BIOQURE_PREPARED_DATA_ROOT
        Directory containing preparation_config.json and preprocessing artifacts.

Example local layout:

    backend/
    ├── bioqure/
    │   └── config.py
    ├── model_artifacts/
    │   └── bioqure/
    │       ├── vqc.model
    │       ├── logistic_regression.joblib
    │       ├── rbf_svm.joblib
    │       ├── vqc_probability_calibrator.joblib
    │       └── metrics.json
    └── prepared_data/
        ├── preparation_config.json
        ├── classical_scaler.joblib
        └── quantum_scaler.joblib
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Project roots
# ---------------------------------------------------------------------------

BIOQURE_PACKAGE_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = BIOQURE_PACKAGE_ROOT.parent
REPO_ROOT = BACKEND_ROOT.parent


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _env_path(name: str, default: Path) -> Path:
    """
    Resolve an environment-variable path or use the supplied default.
    """
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return Path(raw).expanduser().resolve()


# ---------------------------------------------------------------------------
# Artifact roots
# ---------------------------------------------------------------------------

def get_model_root() -> Path:
    """
    Root containing trained BIOQURE inference artifacts.

    Override with:
        BIOQURE_MODEL_ROOT=/absolute/path/to/models
    """
    return _env_path(
        "BIOQURE_MODEL_ROOT",
        BACKEND_ROOT / "model_artifacts" / "bioqure",
    )


def get_prepared_data_root() -> Path:
    """
    Root containing preprocessing artifacts produced by the training pipeline.

    Override with:
        BIOQURE_PREPARED_DATA_ROOT=/absolute/path/to/prepared_data
    """
    return _env_path(
        "BIOQURE_PREPARED_DATA_ROOT",
        BACKEND_ROOT / "prepared_data",
    )


# ---------------------------------------------------------------------------
# Training configuration
# ---------------------------------------------------------------------------

def get_preparation_config_path() -> Path:
    return get_prepared_data_root() / "preparation_config.json"


@lru_cache(maxsize=1)
def load_preparation_config() -> dict[str, Any]:
    """
    Load the exact preparation configuration used by training.

    Feature order must come from this file rather than being independently
    hard-coded in the inference pipeline.
    """
    path = get_preparation_config_path()

    if not path.is_file():
        raise FileNotFoundError(
            "BIOQURE preparation configuration was not found: "
            f"{path}. Set BIOQURE_PREPARED_DATA_ROOT or copy the training "
            "preparation artifacts into backend/prepared_data/."
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid BIOQURE preparation_config.json: {path}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"BIOQURE preparation_config.json must contain a JSON object: {path}"
        )

    return data


def get_feature_names() -> list[str]:
    """
    Return biomarkers in the exact order used by model preparation.
    """
    config = load_preparation_config()

    raw_features = config.get("feature_names")

    if not isinstance(raw_features, list):
        raise ValueError(
            "BIOQURE preparation_config.json is missing a list named "
            "'feature_names'."
        )

    feature_names = [str(x).strip() for x in raw_features]

    if not feature_names:
        raise ValueError("BIOQURE feature_names cannot be empty.")

    if len(feature_names) not in (6, 8):
        raise ValueError(
            f"BIOQURE expects 6 or 8 biomarkers according to the training "
            f"contract, found {len(feature_names)}: {feature_names}"
        )

    if len(feature_names) != len(set(feature_names)):
        raise ValueError(
            f"BIOQURE feature_names contain duplicates: {feature_names}"
        )

    if any(not name for name in feature_names):
        raise ValueError("BIOQURE feature_names cannot contain empty names.")

    return feature_names


def get_class_mapping() -> dict[str, int]:
    """
    Return the training label mapping.

    The preparation pipeline currently defines:
        Normal -> 0
        Tumor  -> 1
    """
    config = load_preparation_config()
    raw_mapping = config.get("class_mapping")

    if isinstance(raw_mapping, dict):
        output: dict[str, int] = {}

        for label, value in raw_mapping.items():
            try:
                output[str(label)] = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid class_mapping entry: {label!r}: {value!r}"
                ) from exc

        if output:
            return output

    # Defensive fallback matching the training preparation contract.
    return {
        "Normal": 0,
        "Tumor": 1,
    }


# ---------------------------------------------------------------------------
# Preprocessing artifacts
# ---------------------------------------------------------------------------

def get_classical_scaler_path() -> Path:
    return get_prepared_data_root() / "classical_scaler.joblib"


def get_quantum_scaler_path() -> Path:
    return get_prepared_data_root() / "quantum_scaler.joblib"


# ---------------------------------------------------------------------------
# Trained model artifacts
# ---------------------------------------------------------------------------

def get_vqc_model_path() -> Path:
    return get_model_root() / "vqc.model"


def get_logistic_regression_model_path() -> Path:
    return get_model_root() / "logistic_regression.joblib"


def get_rbf_svm_model_path() -> Path:
    return get_model_root() / "rbf_svm.joblib"


def get_vqc_calibrator_path() -> Path:
    return get_model_root() / "vqc_probability_calibrator.joblib"


def get_training_metrics_path() -> Path:
    return get_model_root() / "metrics.json"


def get_training_loss_history_path() -> Path:
    return get_model_root() / "vqc_loss_history.csv"


# ---------------------------------------------------------------------------
# General artifact helpers
# ---------------------------------------------------------------------------

def require_file(path: Path, description: str) -> Path:
    """
    Raise a clear error when a required runtime artifact is missing.

    We intentionally do not fabricate model outputs when an artifact is
    unavailable.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Required BIOQURE {description} was not found: {path}"
        )
    return path


def describe_runtime_configuration() -> dict[str, Any]:
    """
    Return non-secret configuration information useful for debugging/API
    readiness checks.
    """
    config_path = get_preparation_config_path()

    return {
        "model_root": str(get_model_root()),
        "prepared_data_root": str(get_prepared_data_root()),
        "preparation_config": str(config_path),
        "preparation_config_exists": config_path.is_file(),
        "feature_names": get_feature_names() if config_path.is_file() else [],
        "class_mapping": get_class_mapping() if config_path.is_file() else {},
        "artifacts": {
            "vqc_model": str(get_vqc_model_path()),
            "logistic_regression": str(get_logistic_regression_model_path()),
            "rbf_svm": str(get_rbf_svm_model_path()),
            "vqc_calibrator": str(get_vqc_calibrator_path()),
            "classical_scaler": str(get_classical_scaler_path()),
            "quantum_scaler": str(get_quantum_scaler_path()),
            "metrics": str(get_training_metrics_path()),
        },
    }


__all__ = [
    "BIOQURE_PACKAGE_ROOT",
    "BACKEND_ROOT",
    "REPO_ROOT",
    "get_model_root",
    "get_prepared_data_root",
    "get_preparation_config_path",
    "load_preparation_config",
    "get_feature_names",
    "get_class_mapping",
    "get_classical_scaler_path",
    "get_quantum_scaler_path",
    "get_vqc_model_path",
    "get_logistic_regression_model_path",
    "get_rbf_svm_model_path",
    "get_vqc_calibrator_path",
    "get_training_metrics_path",
    "get_training_loss_history_path",
    "require_file",
    "describe_runtime_configuration",
]