"""
BIOQURE Pydantic API models.

Defines the JSON contracts used between the BIOQURE FastAPI backend and
the React frontend.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PublicDatasetModel(BaseModel):
    dataset_id: str
    name: str
    project: str = "TCGA-BRCA"
    data_type: str = "RNA-seq gene expression"
    access: str = "open"
    description: str = ""

    gdc_file_id: str = ""
    case_id: str = ""
    sample_id: str = ""

    original_filename: str = ""
    download_filename: str = ""

    size_bytes: int | None = None
    sha256: str | None = None

    feature_count: int | None = None
    feature_names: list[str] = Field(default_factory=list)

    sample_type: str | None = None
    tissue_type: str | None = None


class PublicDatasetListResponse(BaseModel):
    status: str = "ok"
    collection_id: str = "bioqure-public-tcga"
    collection_name: str = "BIOQURE Public Dataset Pool"
    count: int
    datasets: list[PublicDatasetModel] = Field(default_factory=list)


class PublicDatasetDetailResponse(BaseModel):
    status: str = "ok"
    dataset: PublicDatasetModel
    metadata: dict[str, Any] = Field(default_factory=dict)


class BiomarkerValueModel(BaseModel):
    gene: str
    tpm: float
    log2_tpm_plus_1: float
    classical_scaled: float
    quantum_scaled: float


class PreprocessingSummaryModel(BaseModel):
    feature_names: list[str] = Field(default_factory=list)
    feature_count: int
    expression_transform: str = "log2(TPM + 1)"
    classical_scaling: str = "Training-fitted StandardScaler"
    quantum_scaling: str = "Training-fitted MinMaxScaler mapped to [0, pi]"
    quantum_feature_min: float | None = None
    quantum_feature_max: float | None = None


class ClassicalModelResult(BaseModel):
    model: str
    display_name: str
    prediction: int
    label: str
    tumor_probability: float | None = None
    decision_score: float | None = None
    display_probability: float | None = None
    probability_calibrated: bool = False
    confidence_percent: float | None = None


class VQCModelResult(BaseModel):
    model: str = "vqc"
    display_name: str = "Variational Quantum Classifier"

    raw_prediction: int
    raw_label: str
    raw_probability: float

    calibrated_probability: float | None = None

    prediction: int
    label: str

    confidence_percent: float | None = None
    probability_calibrated: bool = False
    calibrator_available: bool = False


class ModelSelectionModel(BaseModel):
    selected_model: str
    selected_display_name: str
    reason: str
    best_classical_model: str

    best_classical_validation_balanced_accuracy: float | None = None
    vqc_validation_balanced_accuracy: float | None = None

    selection_uses_test_data: bool = False


class TrainingArtifactStatusModel(BaseModel):
    logistic_regression: bool = False
    rbf_svm: bool = False
    vqc: bool = False
    vqc_calibrator: bool = False


class TrainingSummaryModel(BaseModel):
    feature_names: list[str] = Field(default_factory=list)
    feature_count: int

    configuration: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)

    test_available: bool = False
    test_evaluated: bool = False

    artifacts: TrainingArtifactStatusModel = Field(
        default_factory=TrainingArtifactStatusModel
    )


class BIOQUREAnalysisResponse(BaseModel):
    status: str = "complete"

    dataset_id: str | None = None
    patient_id: str | None = None

    selected_model: str
    selected_model_display_name: str

    prediction: int
    label: str

    tumor_probability: float
    confidence_percent: float

    selection: ModelSelectionModel

    models: dict[str, Any] = Field(default_factory=dict)

    biomarkers: list[BiomarkerValueModel] = Field(default_factory=list)

    preprocessing: PreprocessingSummaryModel | None = None

    training: TrainingSummaryModel | dict[str, Any] = Field(
        default_factory=dict
    )

    warnings: list[str] = Field(default_factory=list)


class PublicDatasetAnalyzeRequest(BaseModel):
    include_biomarkers: bool = True
    include_training_metadata: bool = True


class BIOQURERuntimeStatusModel(BaseModel):
    status: str

    feature_names: list[str] = Field(default_factory=list)
    feature_count: int | None = None

    model_root: str
    prepared_data_root: str

    public_dataset_count: int = 0

    artifacts: dict[str, bool] = Field(default_factory=dict)


__all__ = [
    "PublicDatasetModel",
    "PublicDatasetListResponse",
    "PublicDatasetDetailResponse",
    "BiomarkerValueModel",
    "PreprocessingSummaryModel",
    "ClassicalModelResult",
    "VQCModelResult",
    "ModelSelectionModel",
    "TrainingArtifactStatusModel",
    "TrainingSummaryModel",
    "BIOQUREAnalysisResponse",
    "PublicDatasetAnalyzeRequest",
    "BIOQURERuntimeStatusModel",
]
