"""
BIOQURE expression-data preprocessing.

Converts one raw GDC RNA-seq augmented STAR gene-count TSV into the
model-ready feature vectors expected by the BIOQURE trained models.

Training contract reproduced from the project preparation pipeline:

    raw GDC tpm_unstranded
        -> log2(TPM + 1)
        -> selected biomarkers in training order
        -> StandardScaler                 (classical models)
        -> MinMaxScaler [0, pi]           (quantum/VQC)

Important:
- This module performs inference-time preprocessing only.
- It NEVER fits a scaler.
- It NEVER selects new biomarkers.
- It NEVER trains a model.
- Feature order comes from preparation_config.json.
- Missing biomarker rows are treated as a hard data error.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import (
    get_classical_scaler_path,
    get_feature_names,
    get_quantum_scaler_path,
    require_file,
)


# Raw GDC column names used by the augmented STAR gene-count output.
REQUIRED_GDC_COLUMNS = {
    "gene_id",
    "gene_name",
    "tpm_unstranded",
}


@dataclass(frozen=True)
class PreparedBIOQURESample:
    """
    Model-ready representation of one GDC expression sample.

    Values are stored as plain Python/NumPy objects so the result can be
    passed directly to the inference layer or serialized to JSON later.
    """

    feature_names: list[str]
    raw_tpm: np.ndarray
    log2_tpm1: np.ndarray
    classical_features: np.ndarray
    quantum_features: np.ndarray

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_names": list(self.feature_names),
            "raw_tpm": self.raw_tpm.astype(float).tolist(),
            "log2_tpm1": self.log2_tpm1.astype(float).tolist(),
            "classical_features": self.classical_features.astype(float).tolist(),
            "quantum_features": self.quantum_features.astype(float).tolist(),
        }


def _read_gdc_table_from_bytes(raw: bytes) -> pd.DataFrame:
    """
    Read one raw GDC augmented STAR gene-count TSV from memory.

    GDC files commonly begin with a metadata/comment line such as:
        # gene-model: GENCODE v36

    Pandas ignores those comment lines and uses the actual tabular header.
    """
    if not raw:
        raise ValueError("GDC expression file is empty.")

    try:
        frame = pd.read_csv(
            io.BytesIO(raw),
            sep="\t",
            comment="#",
            dtype={
                "gene_id": "string",
                "gene_name": "string",
                "gene_type": "string",
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            f"Could not parse GDC expression TSV: {exc}"
        ) from exc

    return _validate_gdc_table(frame)


def _read_gdc_table_from_path(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"GDC expression file not found: {path}")

    try:
        frame = pd.read_csv(
            path,
            sep="\t",
            comment="#",
            dtype={
                "gene_id": "string",
                "gene_name": "string",
                "gene_type": "string",
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            f"Could not parse GDC expression TSV {path}: {exc}"
        ) from exc

    return _validate_gdc_table(frame)


def _validate_gdc_table(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Validate the minimum GDC schema required by the BIOQURE pipeline.
    """
    if frame.empty:
        raise ValueError("GDC expression table contains no rows.")

    frame.columns = (
        frame.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    missing = REQUIRED_GDC_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(
            "GDC expression table is missing required columns: "
            f"{sorted(missing)}"
        )

    frame["gene_name"] = frame["gene_name"].astype("string").str.strip()
    frame["gene_id"] = frame["gene_id"].astype("string").str.strip()

    if frame["gene_name"].isna().all():
        raise ValueError("GDC expression table contains no gene_name values.")

    return frame


def read_gdc_expression(
    source: bytes | bytearray | memoryview | str | Path,
) -> pd.DataFrame:
    """
    Read a raw GDC augmented STAR gene-count TSV.

    Accepted sources:
        bytes / bytearray / memoryview
        filesystem path
    """
    if isinstance(source, (bytes, bytearray, memoryview)):
        return _read_gdc_table_from_bytes(bytes(source))

    return _read_gdc_table_from_path(Path(source))


def _coerce_tpm(value: Any, *, gene_name: str) -> float:
    """
    Convert one GDC TPM value to a finite float.

    Empty/non-numeric values are treated as zero, matching the defensive
    fill-zero behavior used by the training preparation pipeline after the
    expression matrix has been constructed.
    """
    if value is None or pd.isna(value):
        return 0.0

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Non-numeric tpm_unstranded value for biomarker {gene_name!r}: "
            f"{value!r}"
        ) from exc

    if not np.isfinite(numeric):
        raise ValueError(
            f"Non-finite tpm_unstranded value for biomarker {gene_name!r}: "
            f"{numeric!r}"
        )

    if numeric < 0:
        raise ValueError(
            f"Negative tpm_unstranded value for biomarker {gene_name!r}: "
            f"{numeric}"
        )

    return numeric


def extract_biomarker_tpm(
    expression: pd.DataFrame,
    feature_names: list[str] | None = None,
) -> np.ndarray:
    """
    Extract biomarkers in the exact training order.

    Training selected features by gene_name, and the model matrix uses those
    gene names as feature columns. Therefore inference uses exact
    gene_name matching against the GDC gene_name column.

    Duplicate rows for a requested biomarker are rejected rather than summed
    or averaged, because silently changing aggregation could make inference
    inconsistent with training.
    """
    features = list(feature_names or get_feature_names())

    if not features:
        raise ValueError("BIOQURE feature list is empty.")

    if "gene_name" not in expression.columns:
        raise ValueError("Expression table does not contain gene_name.")

    matches = expression[expression["gene_name"].isin(features)].copy()

    if matches.empty:
        raise ValueError(
            "None of the BIOQURE biomarkers were found in the GDC file. "
            f"Expected: {features}"
        )

    found = set(matches["gene_name"].dropna().astype(str))
    missing = [gene for gene in features if gene not in found]
    if missing:
        raise ValueError(
            "GDC expression file is missing BIOQURE biomarkers: "
            f"{missing}"
        )

    duplicate_genes = (
        matches["gene_name"]
        .astype(str)
        .value_counts()
        .loc[lambda values: values > 1]
        .index
        .tolist()
    )
    if duplicate_genes:
        raise ValueError(
            "GDC expression file contains duplicate rows for BIOQURE "
            f"biomarker(s): {duplicate_genes}. "
            "Inference was stopped to avoid an aggregation mismatch with training."
        )

    by_gene = matches.set_index(matches["gene_name"].astype(str))

    values: list[float] = []
    for gene in features:
        row = by_gene.loc[gene]
        if isinstance(row, pd.DataFrame):
            # Defensive guard in case index uniqueness changed unexpectedly.
            raise ValueError(
                f"Multiple rows found for BIOQURE biomarker {gene!r}."
            )

        values.append(
            _coerce_tpm(
                row["tpm_unstranded"],
                gene_name=gene,
            )
        )

    return np.asarray(values, dtype=np.float64)


def log2_tpm_plus_one(raw_tpm: np.ndarray) -> np.ndarray:
    """
    Apply the exact expression transform used by the training data:
        log2(TPM + 1)
    """
    values = np.asarray(raw_tpm, dtype=np.float64)

    if values.ndim != 1:
        raise ValueError(
            f"Expected one-dimensional biomarker vector, got shape {values.shape}"
        )

    if not np.all(np.isfinite(values)):
        raise ValueError("Raw TPM vector contains non-finite values.")

    if np.any(values < 0):
        raise ValueError("Raw TPM vector contains negative values.")

    transformed = np.log2(values + 1.0)

    if not np.all(np.isfinite(transformed)):
        raise ValueError("log2(TPM + 1) produced non-finite values.")

    return transformed


def _validate_scaler(scaler: Any, *, name: str, n_features: int) -> None:
    """
    Validate that a persisted sklearn scaler matches the BIOQURE feature
    dimensionality.
    """
    fitted_features = getattr(scaler, "n_features_in_", None)

    if fitted_features is not None and int(fitted_features) != n_features:
        raise ValueError(
            f"{name} expects {fitted_features} features, but BIOQURE has "
            f"{n_features} biomarkers."
        )


def transform_model_features(
    log2_values: np.ndarray,
    feature_names: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply the persisted training-only classical and quantum scalers.

    Returns:
        (classical_features, quantum_features)

    Classical:
        StandardScaler fitted on the complete training split.

    Quantum:
        MinMaxScaler(feature_range=(0, pi), clip=True) fitted on the
        complete training split.
    """
    features = list(feature_names or get_feature_names())
    values = np.asarray(log2_values, dtype=np.float64)

    if values.ndim != 1:
        raise ValueError(
            f"Expected one-dimensional log2 feature vector, got {values.shape}"
        )

    if len(values) != len(features):
        raise ValueError(
            f"Feature vector length {len(values)} does not match "
            f"BIOQURE feature count {len(features)}."
        )

    if not np.all(np.isfinite(values)):
        raise ValueError("log2 feature vector contains non-finite values.")

    classical_path = require_file(
        get_classical_scaler_path(),
        "classical scaler",
    )
    quantum_path = require_file(
        get_quantum_scaler_path(),
        "quantum scaler",
    )

    classical_scaler = joblib.load(classical_path)
    quantum_scaler = joblib.load(quantum_path)

    _validate_scaler(
        classical_scaler,
        name="Classical StandardScaler",
        n_features=len(features),
    )
    _validate_scaler(
        quantum_scaler,
        name="Quantum MinMaxScaler",
        n_features=len(features),
    )

    matrix = values.reshape(1, -1)

    classical = np.asarray(
        classical_scaler.transform(matrix),
        dtype=np.float32,
    ).reshape(-1)

    quantum = np.asarray(
        quantum_scaler.transform(matrix),
        dtype=np.float32,
    ).reshape(-1)

    # The training pipeline uses a MinMaxScaler configured for [0, pi] with
    # clipping. Keep a final numerical guard for floating-point drift.
    quantum = np.clip(quantum, 0.0, np.pi).astype(np.float32)

    if not np.all(np.isfinite(classical)):
        raise ValueError("Classical scaling produced non-finite values.")

    if not np.all(np.isfinite(quantum)):
        raise ValueError("Quantum scaling produced non-finite values.")

    return classical, quantum


def prepare_gdc_expression(
    source: bytes | bytearray | memoryview | str | Path,
    *,
    feature_names: list[str] | None = None,
) -> PreparedBIOQURESample:
    """
    Full inference-time preparation for one raw GDC expression sample.
    """
    features = list(feature_names or get_feature_names())

    expression = read_gdc_expression(source)
    raw_tpm = extract_biomarker_tpm(expression, features)
    log2_values = log2_tpm_plus_one(raw_tpm)

    classical, quantum = transform_model_features(
        log2_values,
        features,
    )

    return PreparedBIOQURESample(
        feature_names=features,
        raw_tpm=raw_tpm,
        log2_tpm1=log2_values,
        classical_features=classical,
        quantum_features=quantum,
    )


def prepare_gdc_bytes(
    raw: bytes,
    *,
    feature_names: list[str] | None = None,
) -> PreparedBIOQURESample:
    """
    Explicit bytes-only convenience wrapper for FastAPI UploadFile and
    backend dataset-pool inference.
    """
    return prepare_gdc_expression(
        raw,
        feature_names=feature_names,
    )


def feature_vector_summary(
    prepared: PreparedBIOQURESample,
) -> list[dict[str, float | str]]:
    """
    Produce a frontend-friendly biomarker summary.
    """
    rows: list[dict[str, float | str]] = []

    for idx, gene in enumerate(prepared.feature_names):
        rows.append(
            {
                "gene": gene,
                "tpm": float(prepared.raw_tpm[idx]),
                "log2_tpm_plus_1": float(prepared.log2_tpm1[idx]),
                "classical_scaled": float(prepared.classical_features[idx]),
                "quantum_scaled": float(prepared.quantum_features[idx]),
            }
        )

    return rows


def preprocessing_metadata(
    prepared: PreparedBIOQURESample,
) -> dict[str, Any]:
    """
    Non-secret metadata describing how the sample was prepared.
    """
    return {
        "feature_names": list(prepared.feature_names),
        "feature_count": len(prepared.feature_names),
        "expression_transform": "log2(TPM + 1)",
        "classical_scaling": "Training-fitted StandardScaler",
        "quantum_scaling": "Training-fitted MinMaxScaler mapped to [0, pi]",
        "quantum_feature_min": float(np.min(prepared.quantum_features)),
        "quantum_feature_max": float(np.max(prepared.quantum_features)),
    }


__all__ = [
    "PreparedBIOQURESample",
    "REQUIRED_GDC_COLUMNS",
    "read_gdc_expression",
    "extract_biomarker_tpm",
    "log2_tpm_plus_one",
    "transform_model_features",
    "prepare_gdc_expression",
    "prepare_gdc_bytes",
    "feature_vector_summary",
    "preprocessing_metadata",
]
