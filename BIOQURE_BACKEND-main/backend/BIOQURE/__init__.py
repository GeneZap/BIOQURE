"""
BIOQURE backend package.

Public imports are kept small so other backend modules can use the
BIOQURE preprocessing and inference pipeline without depending on
implementation details.
"""

from .config import (
    get_class_mapping,
    get_feature_names,
    get_model_root,
    get_prepared_data_root,
    load_preparation_config,
)

from .inference import (
    analyze_prepared_sample,
    clear_model_caches,
    infer_prepared_sample,
    select_validated_model,
    training_summary,
)

from .preprocessing import (
    PreparedBIOQURESample,
    extract_biomarker_tpm,
    feature_vector_summary,
    log2_tpm_plus_one,
    prepare_gdc_bytes,
    prepare_gdc_expression,
    preprocessing_metadata,
    read_gdc_expression,
    transform_model_features,
)

__all__ = [
    # Configuration
    "get_class_mapping",
    "get_feature_names",
    "get_model_root",
    "get_prepared_data_root",
    "load_preparation_config",

    # Preprocessing
    "PreparedBIOQURESample",
    "read_gdc_expression",
    "extract_biomarker_tpm",
    "log2_tpm_plus_one",
    "transform_model_features",
    "prepare_gdc_expression",
    "prepare_gdc_bytes",
    "feature_vector_summary",
    "preprocessing_metadata",

    # Inference
    "analyze_prepared_sample",
    "infer_prepared_sample",
    "select_validated_model",
    "training_summary",
    "clear_model_caches",
]