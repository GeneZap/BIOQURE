from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from inference_service.inference import FEATURE_NAMES, LOCK_SHA256, InferenceError, LockedInferenceEngine, lock_fingerprint, parse_star_counts


ROOT = Path(__file__).resolve().parents[1]


def fixture_bytes() -> bytes:
    return (ROOT / "public_dataset_pool/raw/BRCA-DEMO-001.rna_seq.augmented_star_gene_counts.tsv").read_bytes()


class InferenceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = LockedInferenceEngine()

    def test_exact_eight_gene_order_and_preprocessing(self):
        values = parse_star_counts(fixture_bytes())
        self.assertEqual(list(values), list(FEATURE_NAMES))
        raw = np.asarray([values[gene] for gene in FEATURE_NAMES]).reshape(1, 8)
        logged = np.log2(raw + 1.0)
        self.assertEqual(raw.shape, (1, 8))
        self.assertEqual(logged.shape, (1, 8))
        self.assertTrue(np.all(np.isfinite(logged)))
        self.assertTrue(np.all(logged >= 0.0))

    def test_missing_duplicate_malformed_negative_and_nonnumeric_rejected(self):
        header = "gene_id\tgene_name\tgene_type\ttpm_unstranded\n"
        valid_rows = "".join(f"ENSG{i}\t{gene}\tgene\t1\n" for i, gene in enumerate(FEATURE_NAMES))
        with self.assertRaises(InferenceError):
            parse_star_counts((header + valid_rows.replace("LPL", "OTHER")).encode())
        with self.assertRaises(InferenceError):
            parse_star_counts((header + valid_rows + "ENSGX\tFABP4\tgene\t1\n").encode())
        with self.assertRaises(InferenceError):
            parse_star_counts((header + valid_rows.replace("\t1\n", "\tbad\n", 1)).encode())
        with self.assertRaises(InferenceError):
            parse_star_counts((header + valid_rows.replace("\t1\n", "\t-1\n", 1)).encode())
        with self.assertRaises(InferenceError):
            parse_star_counts(b"not a STAR counts file")

    def test_locked_inference_schema_fixed_aggregation_and_thresholds(self):
        result = self.engine.infer(fixture_bytes(), "demo", "BRCA-DEMO-001", "Primary Tumor")
        self.assertEqual(result["model_lock"]["feature_count"], 8)
        self.assertEqual([row["gene_name"] for row in result["biomarkers"]], list(FEATURE_NAMES))
        self.assertEqual(result["predictions"]["classical_logistic"]["threshold"], 0.50)
        self.assertEqual(result["predictions"]["quantum_candidate_a_mean"]["threshold"], 0.33)
        self.assertEqual(result["predictions"]["quantum_ae_balanced"]["threshold"], 0.34)
        a = result["predictions"]["quantum_candidate_a_mean"]
        self.assertAlmostEqual(a["tumor_probability"], sum(a["seed_probabilities"]) / 5.0)
        for prediction in result["predictions"].values():
            self.assertTrue(0.0 <= prediction["tumor_probability"] <= 1.0)
        self.assertIn("all_models_agree", result["agreement"])

    def test_report_sections_mirror_locked_predictions(self):
        result = self.engine.infer(fixture_bytes(), "demo", "BRCA-DEMO-001", "Primary Tumor")
        classical = result["predictions"]["classical_logistic"]
        candidate_a = result["predictions"]["quantum_candidate_a_mean"]
        self.assertEqual(result["prediction"]["label"], classical["predicted_class"])
        self.assertEqual(result["prediction"]["tumor_probability"], classical["tumor_probability"])
        self.assertEqual(result["quantum"]["tumor_probability"], candidate_a["tumor_probability"])
        self.assertEqual(result["quantum"]["scaled_features"], [row["quantum_angle"] for row in result["biomarkers"]])
        self.assertEqual(result["quantum"]["qubits"], 8)
        self.assertAlmostEqual(result["quantum"]["angle_bounds"]["max"], np.pi / 2)
        self.assertTrue(all(0.0 <= angle <= np.pi / 2 for angle in result["quantum"]["scaled_features"]))
        self.assertNotIn("checks", result["benchmark"])
        for section in (result, result["prediction"], result["benchmark"]):
            self.assertEqual(section["selected_model_key"], "logistic_regression")
        self.assertIn("logistic_regression", result["benchmark"]["models"])
        self.assertIn("logistic_regression", result["classical_models"])
        self.assertEqual(result["quantum"]["shots"], 2048)
        self.assertEqual(result["input_metrics"]["biomarkers_used"], 8)
        self.assertGreater(result["input_metrics"]["genes_detected"], 8)
        self.assertEqual(list(result["input_metrics"]["biomarker_values_used"]), list(FEATURE_NAMES))
        models = result["benchmark"]["models"]
        self.assertEqual(set(models), {"logistic_regression", "quantum_candidate_a_mean", "quantum_ae_balanced"})
        self.assertAlmostEqual(models["quantum_candidate_a_mean"]["accuracy"], 0.959184)
        self.assertAlmostEqual(models["quantum_candidate_a_mean"]["f1"], 2 * 219 / (2 * 219 + 7 + 3))
        importances = [row["importance"] for row in result["biomarkers"]]
        self.assertEqual(max(importances), 1.0)
        self.assertTrue(all(0.0 <= value <= 1.0 for value in importances))
        self.assertEqual([row["gene"] for row in result["biomarkers"]], list(FEATURE_NAMES))

    def test_demo_pool_is_training_only_and_hashes_are_unchanged(self):
        pool = json.loads((ROOT / "public_dataset_pool/catalog.json").read_text())
        self.assertEqual(len(pool), 15)
        self.assertEqual(sum(item["sample_type"] == "Primary Tumor" for item in pool), 8)
        self.assertEqual(sum(item["sample_type"] == "Solid Tissue Normal" for item in pool), 7)
        self.assertTrue(all(item["split"] == "train" for item in pool))
        self.assertTrue(all((ROOT / "public_dataset_pool/raw" / f"{item['demo_id']}.rna_seq.augmented_star_gene_counts.tsv").is_file() for item in pool))
        lock = ROOT / "configs/final_model_lock.json"
        self.assertEqual(lock_fingerprint(lock), LOCK_SHA256)
        self.assertEqual(self.engine.lock_hash, LOCK_SHA256)
        self.assertFalse((ROOT / "reports/final_test_metrics.json").exists())


if __name__ == "__main__":
    unittest.main()