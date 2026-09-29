"""BIOQURE path and training-configuration helpers."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

PREPARED_DATA_ROOT = Path(
    os.getenv("BIOQURE_PREPARED_DATA_ROOT", str(BACKEND_ROOT / "prepared_data"))
).expanduser().resolve()

MODEL_ROOT = Path(
    os.getenv("BIOQURE_MODEL_ROOT", str(BACKEND_ROOT / "model_artifacts" / "bioqure"))
).expanduser().resolve()

PREPARATION_CONFIG_PATH = Path(
    os.getenv(
        "BIOQURE_PREPARATION_CONFIG",
        str(PREPARED_DATA_ROOT / "preparation_config.json"),
    )
).expanduser().resolve()

DEFAULT_FEATURE_NAMES = [
    "DES",
    "PDK4",
    "PLIN4",
    "MYBPC1",
    "SYNM",
    "ACTA1",
    "SAA1",
    "HBB",
]


def _load_preparation_config() -> dict[str, Any]:
    if not PREPARATION_CONFIG_PATH.is_file():
        return {}
    try:
        payload = json.loads(PREPARATION_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def get_feature_names() -> list[str]:
    config = _load_preparation_config()
    raw = config.get("feature_names") or config.get("features")
    if isinstance(raw, list) and raw:
        return [str(value) for value in raw]
    return list(DEFAULT_FEATURE_NAMES)


def get_datasets_root() -> Path:
    raw = os.getenv("BIOQURE_DATASETS_ROOT")
    if raw:
        return Path(raw).expanduser().resolve()
    return (REPO_ROOT / "data" / "datasets").resolve()


def get_model_root() -> Path:
    return MODEL_ROOT


def get_prepared_data_root() -> Path:
    return PREPARED_DATA_ROOT


def get_classical_scaler_path() -> Path:
    candidates = [
        PREPARED_DATA_ROOT / "classical_scaler.joblib",
        PREPARED_DATA_ROOT / "classical_scaler.pkl",
        MODEL_ROOT / "classical_scaler.joblib",
    ]
    return next((p for p in candidates if p.is_file()), candidates[0])


def get_quantum_scaler_path() -> Path:
    candidates = [
        PREPARED_DATA_ROOT / "quantum_scaler.joblib",
        PREPARED_DATA_ROOT / "quantum_scaler.pkl",
        MODEL_ROOT / "quantum_scaler.joblib",
    ]
    return next((p for p in candidates if p.is_file()), candidates[0])


def get_logistic_regression_model_path() -> Path:
    return MODEL_ROOT / "logistic_regression.joblib"


def get_rbf_svm_model_path() -> Path:
    return MODEL_ROOT / "rbf_svm.joblib"


def get_vqc_model_path() -> Path:
    return MODEL_ROOT / "vqc.model"


def get_vqc_calibrator_path() -> Path:
    return MODEL_ROOT / "vqc_probability_calibrator.joblib"


def get_training_metrics_path() -> Path:
    return MODEL_ROOT / "metrics.json"


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(
            f"BIOQURE {label} not found: {path}"
        )
    return path


def describe_runtime_configuration() -> dict[str, Any]:
    feature_names = get_feature_names()
    artifact_paths = {
        "logistic_regression": get_logistic_regression_model_path(),
        "rbf_svm": get_rbf_svm_model_path(),
        "vqc": get_vqc_model_path(),
        "vqc_calibrator": get_vqc_calibrator_path(),
        "metrics": get_training_metrics_path(),
        "classical_scaler": get_classical_scaler_path(),
        "quantum_scaler": get_quantum_scaler_path(),
        "preparation_config": PREPARATION_CONFIG_PATH,
    }
    return {
        "feature_names": feature_names,
        "feature_count": len(feature_names),
        "model_root": str(MODEL_ROOT),
        "prepared_data_root": str(PREPARED_DATA_ROOT),
        "artifacts": {
            name: path.is_file()
            for name, path in artifact_paths.items()
        },
        "artifact_paths": {
            name: str(path)
            for name, path in artifact_paths.items()
        },
    }


__all__ = [
    "BACKEND_ROOT",
    "REPO_ROOT",
    "PREPARED_DATA_ROOT",
    "MODEL_ROOT",
    "PREPARATION_CONFIG_PATH",
    "get_feature_names",
    "get_datasets_root",
    "get_model_root",
    "get_prepared_data_root",
    "get_classical_scaler_path",
    "get_quantum_scaler_path",
    "get_logistic_regression_model_path",
    "get_rbf_svm_model_path",
    "get_vqc_model_path",
    "get_vqc_calibrator_path",
    "get_training_metrics_path",
    "require_file",
    "describe_runtime_configuration",
]
