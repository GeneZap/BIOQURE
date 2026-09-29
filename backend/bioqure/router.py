"""
BIOQURE FastAPI routes.

Public endpoints for the curated TCGA/GDC expression dataset pool and
BIOQURE model inference.

Routes:
    GET  /bioqure/datasets/public
    GET  /bioqure/datasets/public/{dataset_id}
    GET  /bioqure/datasets/public/{dataset_id}/download
    POST /bioqure/datasets/public/{dataset_id}/analyze
    GET  /bioqure/status

This router is intentionally separate from the legacy /datasets and /analyze
GeneZap FASTA endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .config import (
    describe_runtime_configuration,
    get_feature_names,
    get_model_root,
    get_prepared_data_root,
)
from .dataset_repository import (
    BIOQUREPublicDatasetRepository,
)
from .inference import (
    analyze_prepared_sample,
    training_summary,
)
from .models import (
    BIOQUREAnalysisResponse,
    BIOQURERuntimeStatusModel,
    BiomarkerValueModel,
    ModelSelectionModel,
    PreprocessingSummaryModel,
    PublicDatasetAnalyzeRequest,
    PublicDatasetDetailResponse,
    PublicDatasetListResponse,
    PublicDatasetModel,
    TrainingArtifactStatusModel,
    TrainingSummaryModel,
)
from .preprocessing import (
    prepare_gdc_bytes,
    preprocessing_metadata,
)


router = APIRouter(
    prefix="/bioqure",
    tags=["bioqure"],
)

_repo = BIOQUREPublicDatasetRepository()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_public_dataset_model(
    record: dict[str, Any],
) -> PublicDatasetModel:
    """
    Convert a repository catalog record into the public API model.
    """
    return PublicDatasetModel(
        dataset_id=str(record["dataset_id"]),
        name=str(record.get("name") or record["dataset_id"]),
        project=str(record.get("project") or "TCGA-BRCA"),
        data_type=str(
            record.get("data_type")
            or "RNA-seq gene expression"
        ),
        access=str(record.get("access") or "open"),
        description=str(record.get("description") or ""),
        gdc_file_id=str(record.get("gdc_file_id") or ""),
        case_id=str(record.get("case_id") or ""),
        sample_id=str(record.get("sample_id") or ""),
        original_filename=str(
            record.get("original_filename") or ""
        ),
        download_filename=str(
            record.get("download_filename") or ""
        ),
        size_bytes=(
            int(record["size_bytes"])
            if record.get("size_bytes") is not None
            else None
        ),
        sha256=(
            str(record["sha256"])
            if record.get("sha256")
            else None
        ),
        feature_count=(
            int(record["feature_count"])
            if record.get("feature_count") is not None
            else None
        ),
        feature_names=[
            str(x)
            for x in (record.get("feature_names") or [])
        ],
        sample_type=(
            str(record["sample_type"])
            if record.get("sample_type") is not None
            else None
        ),
        tissue_type=(
            str(record["tissue_type"])
            if record.get("tissue_type") is not None
            else None
        ),
    )


def _repository_not_found(message: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=message,
    )


def _analysis_response(
    result: dict[str, Any],
    *,
    dataset_id: str,
    include_biomarkers: bool,
    include_training_metadata: bool,
) -> BIOQUREAnalysisResponse:
    """
    Convert inference output into the public API response.

    The inference layer remains the source of model outputs. This helper
    only removes optional sections requested by the caller and attaches
    preprocessing metadata.
    """
    prepared_biomarkers = list(
        result.get("biomarkers") or []
    )

    if not include_biomarkers:
        prepared_biomarkers = []

    training = result.get("training") or {}

    if not include_training_metadata:
        training = {
            "feature_names": result.get(
                "training",
                {},
            ).get("feature_names", get_feature_names())
            if isinstance(result.get("training"), dict)
            else get_feature_names(),
            "feature_count": len(get_feature_names()),
            "configuration": {},
            "validation": {},
            "test_available": False,
            "test_evaluated": False,
            "artifacts": {},
        }

    selection_raw = dict(
        result.get("selection") or {}
    )

    selection = ModelSelectionModel(
        selected_model=str(
            selection_raw.get("selected_model")
            or result.get("selected_model")
            or ""
        ),
        selected_display_name=str(
            selection_raw.get("selected_display_name")
            or result.get("selected_model_display_name")
            or ""
        ),
        reason=str(
            selection_raw.get("reason")
            or ""
        ),
        best_classical_model=str(
            selection_raw.get("best_classical_model")
            or ""
        ),
        best_classical_validation_balanced_accuracy=(
            float(
                selection_raw["best_classical_validation_balanced_accuracy"]
            )
            if selection_raw.get(
                "best_classical_validation_balanced_accuracy"
            ) is not None
            else None
        ),
        vqc_validation_balanced_accuracy=(
            float(
                selection_raw["vqc_validation_balanced_accuracy"]
            )
            if selection_raw.get(
                "vqc_validation_balanced_accuracy"
            ) is not None
            else None
        ),
        selection_uses_test_data=bool(
            selection_raw.get(
                "selection_uses_test_data",
                False,
            )
        ),
    )

    preprocessing = result.get("preprocessing")

    preprocessing_model = (
        PreprocessingSummaryModel(**preprocessing)
        if isinstance(preprocessing, dict)
        else None
    )

    if isinstance(training, dict):
        training_configuration = training.get("configuration") or {}
        validation = training.get("validation") or {}
        artifacts = training.get("artifacts") or {}

        training_model = TrainingSummaryModel(
            feature_names=[
                str(x)
                for x in (
                    training.get("feature_names")
                    or get_feature_names()
                )
            ],
            feature_count=int(
                training.get(
                    "feature_count",
                    len(get_feature_names()),
                )
            ),
            configuration=dict(training_configuration),
            validation=dict(validation),
            test_available=bool(
                training.get("test_available", False)
            ),
            test_evaluated=bool(
                training.get("test_evaluated", False)
            ),
            artifacts=TrainingArtifactStatusModel(
                logistic_regression=bool(
                    artifacts.get(
                        "logistic_regression",
                        False,
                    )
                ),
                rbf_svm=bool(
                    artifacts.get(
                        "rbf_svm",
                        False,
                    )
                ),
                vqc=bool(
                    artifacts.get("vqc", False)
                ),
                vqc_calibrator=bool(
                    artifacts.get(
                        "vqc_calibrator",
                        False,
                    )
                ),
            ),
        )
    else:
        training_model = TrainingSummaryModel(
            feature_names=get_feature_names(),
            feature_count=len(get_feature_names()),
        )

    model = BIOQUREAnalysisResponse(
        status=str(
            result.get("status") or "complete"
        ),
        dataset_id=dataset_id,
        patient_id=(
            str(result["patient_id"])
            if result.get("patient_id") is not None
            else None
        ),
        selected_model=str(
            result.get("selected_model") or ""
        ),
        selected_model_display_name=str(
            result.get(
                "selected_model_display_name"
            )
            or ""
        ),
        prediction=int(
            result.get("prediction", 0)
        ),
        label=str(
            result.get("label") or ""
        ),
        tumor_probability=float(
            result.get("tumor_probability", 0.0)
        ),
        confidence_percent=float(
            result.get("confidence_percent", 0.0)
        ),
        selection=selection,
        models=dict(
            result.get("models") or {}
        ),
        biomarkers=[
            BiomarkerValueModel(**row)
            for row in prepared_biomarkers
        ],
        preprocessing=preprocessing_model,
        training=training_model,
        warnings=[
            str(x)
            for x in (result.get("warnings") or [])
        ],
    )

    return model


# ---------------------------------------------------------------------------
# Public dataset catalog
# ---------------------------------------------------------------------------

@router.get(
    "/datasets/public",
    response_model=PublicDatasetListResponse,
)
def list_public_datasets() -> PublicDatasetListResponse:
    """
    Return the curated public BIOQURE dataset catalog.

    The frontend uses this endpoint to populate the dataset pool.
    """
    try:
        records = _repo.list_public_datasets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Could not load BIOQURE public dataset catalog: {exc}",
        ) from exc

    return PublicDatasetListResponse(
        status="ok",
        collection_id="bioqure-public-tcga",
        collection_name="BIOQURE Public Dataset Pool",
        count=len(records),
        datasets=[
            _to_public_dataset_model(record)
            for record in records
        ],
    )


@router.get(
    "/datasets/public/{dataset_id}",
    response_model=PublicDatasetDetailResponse,
)
def get_public_dataset(
    dataset_id: str,
) -> PublicDatasetDetailResponse:
    """
    Return metadata for one public dataset.
    """
    try:
        record = _repo.get_public_dataset(dataset_id)
        metadata = _repo.read_dataset_metadata(dataset_id)
    except KeyError:
        raise _repository_not_found(
            "BIOQURE public dataset not found."
        )
    except FileNotFoundError:
        raise _repository_not_found(
            "BIOQURE public dataset expression file not found."
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Could not load BIOQURE dataset: {exc}",
        ) from exc

    return PublicDatasetDetailResponse(
        status="ok",
        dataset=_to_public_dataset_model(record),
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Public dataset download
# ---------------------------------------------------------------------------

@router.get(
    "/datasets/public/{dataset_id}/download",
)
def download_public_dataset(
    dataset_id: str,
) -> Response:
    """
    Download the expression file attached to one public dataset.

    This is a read-only endpoint. No arbitrary filesystem path is accepted.
    """
    try:
        data, filename = _repo.read_expression_bytes(
            dataset_id
        )
    except KeyError:
        raise _repository_not_found(
            "BIOQURE public dataset not found."
        )
    except FileNotFoundError:
        raise _repository_not_found(
            "BIOQURE public dataset expression file not found."
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Could not read BIOQURE dataset: {exc}",
        ) from exc

    # Prevent a malformed catalog filename from injecting response headers.
    safe_filename = (
        str(filename)
        .replace("\r", "")
        .replace("\n", "")
        .replace('"', "")
        .replace("/", "_")
        .replace("\\", "_")
    ).strip() or "expression.tsv"

    return Response(
        content=data,
        media_type="text/tab-separated-values",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{safe_filename}"'
            ),
            "Cache-Control": "public, max-age=3600",
        },
    )


# ---------------------------------------------------------------------------
# Public dataset analysis
# ---------------------------------------------------------------------------

@router.post(
    "/datasets/public/{dataset_id}/analyze",
    response_model=BIOQUREAnalysisResponse,
)
def analyze_public_dataset(
    dataset_id: str,
    body: PublicDatasetAnalyzeRequest | None = None,
) -> BIOQUREAnalysisResponse:
    """
    Load one backend-hosted public dataset and run BIOQURE inference.
    """
    options = body or PublicDatasetAnalyzeRequest()

    try:
        # Read only the dataset selected by ID.
        raw, _filename = _repo.read_expression_bytes(
            dataset_id
        )
    except KeyError:
        raise _repository_not_found(
            "BIOQURE public dataset not found."
        )
    except FileNotFoundError:
        raise _repository_not_found(
            "BIOQURE public dataset expression file not found."
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Could not load BIOQURE dataset: {exc}",
        ) from exc

    try:
        # Preprocessing performs inference-time transforms only. It does not
        # fit new scalers or select new biomarkers.
        prepared = prepare_gdc_bytes(raw)

        result = analyze_prepared_sample(prepared)

        # Attach transformation metadata for the frontend.
        result["dataset_id"] = dataset_id
        result["preprocessing"] = preprocessing_metadata(
            prepared
        )

        # Keep the original GDC/BIOQURE sample identifier visible when
        # supplied through metadata.
        try:
            dataset_record = _repo.get_public_dataset(
                dataset_id
            )
            result["patient_id"] = (
                dataset_record.get("sample_id")
                or dataset_record.get("case_id")
                or dataset_id
            )
        except Exception:
            result["patient_id"] = dataset_id

    except FileNotFoundError as exc:
        # Usually a missing scaler/model artifact.
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        # Usually Qiskit/model-runtime loading problems.
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"BIOQURE analysis failed: {exc}",
        ) from exc

    return _analysis_response(
        result,
        dataset_id=dataset_id,
        include_biomarkers=options.include_biomarkers,
        include_training_metadata=options.include_training_metadata,
    )


# ---------------------------------------------------------------------------
# Runtime / deployment status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    response_model=BIOQURERuntimeStatusModel,
)
def bioqure_status() -> BIOQURERuntimeStatusModel:
    """
    Non-secret BIOQURE runtime diagnostics.

    Useful for confirming deployment configuration before running a dataset.
    """
    try:
        runtime = describe_runtime_configuration()
        summary = _repo.public_catalog_summary()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"BIOQURE runtime configuration is unavailable: {exc}",
        ) from exc

    return BIOQURERuntimeStatusModel(
        status="ready",
        feature_names=[
            str(x)
            for x in (runtime.get("feature_names") or [])
        ],
        feature_count=(
            len(runtime.get("feature_names") or [])
        ),
        model_root=str(
            get_model_root()
        ),
        prepared_data_root=str(
            get_prepared_data_root()
        ),
        public_dataset_count=int(
            summary.get("count", 0)
        ),
        artifacts=dict(
            (
                runtime.get("artifacts")
                or {}
            )
        ),
    )


__all__ = ["router"]
