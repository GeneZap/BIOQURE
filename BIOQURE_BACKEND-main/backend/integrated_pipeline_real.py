"""Adapter for the hackathon CLI pipeline to be callable from the API.

The original `CV_HACKATHON_MODEL_DATASET/INTEGRATED_AMR_PIPELINE_REAL.py` is an
interactive CLI script (uses `input()` + prints). The FastAPI backend needs a
callable function that returns structured JSON instead.

NOTE: Models are LAZILY LOADED to minimize RAM footprint on free-tier Render.
Only requested engines are loaded into memory; models are garbage-collected
after inference to prevent 512MB OOM crashes.
"""

from __future__ import annotations

import base64
import gc
import io
import logging
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import matplotlib
import numpy as np
import pandas as pd
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

_log = logging.getLogger("genezap.integrated_pipeline")


def _env_true(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _cv_artifact_root() -> Path:
    """
    Root folder containing V1_Model_Output, V2_Model_Output, etc.

    Override with GENEZAP_CV_ARTIFACT_ROOT for Docker / monorepo layouts
    (default: <repo>/CV_HACKATHON_MODEL_DATASET next to `backend/`).
    """
    override = os.environ.get("GENEZAP_CV_ARTIFACT_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    backend_dir = Path(__file__).resolve().parent
    return (backend_dir.parent / "CV_HACKATHON_MODEL_DATASET").resolve()


def _artifact_dirs() -> dict[str, Path]:
    root = _cv_artifact_root()
    return {
        "root": root,
        "v1": root / "V1_Model_Output",
        "v2": root / "V2_Model_Output",
        "v3": root / "V3_Model_Output",
        "v4": root / "V4_GENE_DETECTION",
        "card": root / "MAIN_MODEL" / "CARD_DB.fasta",
    }


def _load_tf_model(path: Path):
    # TensorFlow is an optional heavyweight dependency at runtime.
    if not path.is_file():
        raise FileNotFoundError(f"V3 Keras model not found: {path}")
    try:
        from tensorflow import keras  # type: ignore

        return keras.models.load_model(path)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Failed to load V3 model from {path}: {e}") from e


def _cgr_png_base64(sequence: str) -> str:
    """Generate a simple CGR scatter plot as base64 PNG."""
    coords = {"A": (0.0, 0.0), "T": (1.0, 0.0), "G": (1.0, 1.0), "C": (0.0, 1.0)}
    pos = np.array([0.5, 0.5], dtype=np.float64)
    points: list[tuple[float, float]] = []

    seq = sequence.replace("N", "")
    if not seq:
        return ""

    mid = len(seq) // 2
    window = seq[max(0, mid - 25000) : min(len(seq), mid + 25000)]
    for base in window:
        c = coords.get(base)
        if c is None:
            continue
        pos = (pos + np.array(c, dtype=np.float64)) / 2.0
        points.append((float(pos[0]), float(pos[1])))

    if not points:
        return ""

    arr = np.array(points, dtype=np.float64)
    fig = plt.figure(figsize=(5, 5), dpi=110, facecolor="black")
    ax = fig.add_subplot(1, 1, 1)
    ax.scatter(arr[:, 0], arr[:, 1], s=0.5, c="cyan", alpha=0.9, marker=".")
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, facecolor="black")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _v4_detect_card_genes(sequence: str, v4_dir: Path, card_fasta: Path) -> list[dict[str, Any]]:
    """Best-effort CARD gene detection via hackathon detector if present."""
    try:
        import sys

        sys.path.append(str(v4_dir))
        from V4_GENE_DET import detect_card_genes  # type: ignore

        if card_fasta.is_file():
            return list(detect_card_genes(sequence, str(card_fasta)))  # type: ignore[arg-type]
        return []
    except Exception:
        return []


def run_integrated_real_engines(
    sequence: str,
    *,
    header: str | None,
    genome_id: str | None = None,
) -> dict[str, Any]:
    """Run the hackathon 'integrated real' pipeline and return an engines dict.

    This is intended to plug into `backend/analysis.py` in place of `run_quad_engines`.
    """
    dirs = _artifact_dirs()
    v1_dir, v2_dir, v3_dir = dirs["v1"], dirs["v2"], dirs["v3"]
    v4_dir, card_fasta = dirs["v4"], dirs["card"]

    _log.info("Integrated pipeline artifact root: %s", dirs["root"])
    v1_pkl = v1_dir / "bacterial_id_model.pkl"
    if not v1_pkl.is_file():
        raise FileNotFoundError(
            f"Integrated V1 model missing at {v1_pkl}. "
            f"Set GENEZAP_CV_ARTIFACT_ROOT or place CV_HACKATHON_MODEL_DATASET next to the backend folder."
        )

    skip_v3 = _env_true("GENEZAP_SKIP_TENSORFLOW") or _env_true("GENEZAP_INTEGRATED_DISABLE_V3")
    if skip_v3:
        _log.warning("V3 disabled via env flag (GENEZAP_SKIP_TENSORFLOW/GENEZAP_INTEGRATED_DISABLE_V3)")

    # Make TF a bit quieter if it exists.
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

    # --- V1 ---
    v1_model = joblib.load(v1_dir / "bacterial_id_model.pkl")
    le_id = joblib.load(v1_dir / "label_encoder_id.pkl")
    try:
        # Load V1 feature columns from pickle file (models from training may not have feature_names_in_)
        v1_feat_file = v1_dir / "v1_feature_columns.pkl"
        if v1_feat_file.is_file():
            v1_feat = joblib.load(v1_feat_file)
        else:
            # Fallback: try to get from model object (sklearn >= 0.24 may have this)
            v1_feat = list(getattr(v1_model, "feature_names_in_", []))

        if not v1_feat:
            raise ValueError(
                "V1 model feature names not found. "
                "Ensure v1_feature_columns.pkl exists in V1_Model_Output directory."
            )

        # Filter to keep only valid k-mers (ACGT sequences), drop metadata columns
        valid_kmers = [f for f in v1_feat if isinstance(f, str) and len(f) > 0 and all(c in "ACGT" for c in f.upper())]
        if not valid_kmers:
            # If no valid k-mers found, use original list (might be numeric k-mer indices)
            valid_kmers = v1_feat

        k_len = len(valid_kmers[0]) if valid_kmers and isinstance(valid_kmers[0], str) else 6
        kmers = Counter(sequence[i : i + k_len] for i in range(max(0, len(sequence) - k_len + 1)))
        test_row_v1 = [kmers.get(name, 0) for name in valid_kmers]

        v1_species = le_id.inverse_transform(
            v1_model.predict(pd.DataFrame([test_row_v1], columns=valid_kmers))
        )[0]
    finally:
        # Free V1 artifacts before loading V2/V3 to reduce peak RAM.
        del v1_model, le_id
        gc.collect()

    v1_out = {
        "engine": "V1",
        "engine_name": "Genomic Profiler",
        "status": "complete",
        "mode": "artifact",
        "taxonomy": {"species": str(v1_species)},
        "notes": "Sourced from CV_HACKATHON_MODEL_DATASET V1_Model_Output artifacts.",
    }

    # --- V2 ---
    v2_model = joblib.load(v2_dir / "v2_multi_input_model_FIXED.pkl")
    v2_features = joblib.load(v2_dir / "v2_feature_columns_FIXED.pkl")
    try:
        v2_kmers = Counter(sequence[i : i + 6] for i in range(max(0, len(sequence) - 6 + 1)))
        antibiotics = [col.replace("Drug_", "") for col in v2_features if str(col).startswith("Drug_")]
        results_v2: list[dict[str, Any]] = []
        for ab in antibiotics:
            features = {col: 0 for col in v2_features}
            for kmer, count in v2_kmers.items():
                if kmer in features:
                    features[kmer] = count
            drug_col = f"Drug_{ab}"
            if drug_col in features:
                features[drug_col] = 1
            X = pd.DataFrame([features])[v2_features]
            pred = int(v2_model.predict(X)[0])
            proba = v2_model.predict_proba(X)[0]
            results_v2.append(
                {
                    "drug": ab,
                    "status": "RESISTANT" if pred == 1 else "SUSCEPTIBLE",
                    "confidence": float(proba[1] if pred == 1 else proba[0]),
                }
            )
    finally:
        # Free V2 artifacts before loading V3/TensorFlow.
        del v2_model, v2_features
        gc.collect()

    resistant = [r for r in results_v2 if r["status"] == "RESISTANT"]
    v2_out = {
        "engine": "V2",
        "engine_name": "Pharmacology",
        "status": "complete",
        "mode": "artifact",
        "pharmacology": {
            "panel": results_v2,
            "resistant_count": len(resistant),
            "susceptible_count": len(results_v2) - len(resistant),
            "genome_id": genome_id or "",
        },
        "notes": "Sourced from CV_HACKATHON_MODEL_DATASET V2_Model_Output artifacts.",
    }

    # --- V3 ---
    cgr_b64 = _cgr_png_base64(sequence)
    v3_prob = 0.5
    if not skip_v3:
        tmp_path = ""
        v3_model = None
        try:
            v3_model = _load_tf_model(v3_dir / "v3_vision_model.h5")

            # Reuse the generated PNG by decoding it into an array if available.
            # If we couldn't generate it, fall back to a neutral verdict.
            if cgr_b64:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(base64.b64decode(cgr_b64.encode("ascii")))
                    tmp_path = tmp.name
                img = Image.open(tmp_path).convert("RGB").resize((256, 256))
                img_array = np.expand_dims(np.asarray(img, dtype=np.float32) / 255.0, axis=0)
                v3_prob = float(v3_model.predict(img_array, verbose=0)[0][0])
        except Exception as e:  # noqa: BLE001
            _log.warning("V3 inference skipped/fallback due to error: %s", e)
            v3_prob = 0.5
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            if v3_model is not None:
                try:
                    del v3_model
                except Exception:
                    pass
            try:
                from tensorflow.keras import backend as keras_backend  # type: ignore

                keras_backend.clear_session()
            except Exception:
                pass
            gc.collect()

    v3_verdict = "RESISTANT" if v3_prob < 0.5 else "SUSCEPTIBLE"
    v3_out = {
        "engine": "V3",
        "engine_name": "Vision",
        "status": "complete",
        "mode": "artifact",
        "vision": {
            "clinical_verdict": v3_verdict,
            "confidence_percent": round(abs(v3_prob - 0.5) * 200.0, 2),
            "cgr": {"image_png_base64": cgr_b64, "label": "Chaos game representation (CGR)"},
        },
        "notes": "Sourced from CV_HACKATHON_MODEL_DATASET V3_Model_Output artifacts.",
    }

    # --- V4 ---
    detected_genes = _v4_detect_card_genes(sequence, v4_dir, card_fasta)
    if detected_genes:
        # Mirror the CLI behavior: if V4 sees hits, V3 should be treated as resistant.
        v3_out["vision"]["clinical_verdict"] = "RESISTANT"

    hits = []
    for g in detected_genes:
        hits.append(
            {
                "gene": g.get("gene_name") or g.get("gene") or "",
                "aro_id": g.get("aro_id") or "",
                "mechanism": g.get("mechanism") or "",
            }
        )

    v4_out = {
        "engine": "V4",
        "engine_name": "Discovery",
        "status": "complete",
        "mode": "artifact",
        "discovery": {"hits": hits},
        "notes": "Best-effort CARD scan via CV_HACKATHON_MODEL_DATASET V4_GENE_DETECTION.",
    }

    gc.collect()

    return {"v1": v1_out, "v2": v2_out, "v3": v3_out, "v4": v4_out}

