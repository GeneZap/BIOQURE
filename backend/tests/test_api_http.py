from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid

os.environ.setdefault("BIOQURE_CORS_ORIGINS", "http://localhost:5173")

from http.server import ThreadingHTTPServer  # noqa: E402

from inference_service.inference import LOCK_SHA256  # noqa: E402
from inference_service.server import Handler  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "public_dataset_pool/raw/BRCA-DEMO-001.rna_seq.augmented_star_gene_counts.tsv"
ALLOWED_ORIGIN = "http://localhost:5173"


class ApiHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, path, method="GET", body=None, headers=None):
        request = Request(f"{self.base}{path}", data=body, method=method, headers=headers or {})
        try:
            with urlopen(request, timeout=120) as response:
                raw = response.read()
                return response.status, response.headers, json.loads(raw) if raw else None
        except HTTPError as error:
            raw = error.read()
            return error.code, error.headers, json.loads(raw) if raw else None

    def multipart(self, filename: str, content: bytes):
        boundary = uuid.uuid4().hex
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            "Content-Type: text/tab-separated-values\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        return body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}

    def test_health_get_head_and_query_string(self):
        status, _, payload = self.call("/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["model_lock_sha256"], LOCK_SHA256)
        status, headers, payload = self.call("/api/v1/health", method="HEAD")
        self.assertEqual(status, 200)
        self.assertIsNone(payload)
        self.assertGreater(int(headers["Content-Length"]), 0)
        self.assertEqual(self.call("/api/v1/health?probe=1")[0], 200)
        self.assertEqual(self.call("/")[0], 200)

    def test_model_info_and_demo_samples(self):
        status, _, info = self.call("/api/v1/model-info")
        self.assertEqual(status, 200)
        self.assertEqual(info["feature_count"], 8)
        self.assertEqual(info["thresholds"], {"classical_logistic": 0.5, "quantum_candidate_a_mean": 0.33, "quantum_ae_balanced": 0.34})
        status, _, demo = self.call("/api/v1/demo-samples")
        self.assertEqual(status, 200)
        self.assertEqual(len(demo["samples"]), 15)
        self.assertTrue(all("fixture_path" not in sample for sample in demo["samples"]))

    def test_demo_prediction_returns_locked_and_report_sections(self):
        for demo_id, label in (("BRCA-DEMO-001", "Primary Tumor"), ("BRCA-DEMO-009", "Solid Tissue Normal")):
            status, _, result = self.call(f"/api/v1/predict/demo/{demo_id}", method="POST", body=b"{}", headers={"Content-Type": "application/json"})
            self.assertEqual(status, 200, result)
            self.assertEqual(result["source"]["known_research_label"], label)
            for key in ("predictions", "biomarkers", "agreement", "timing_ms", "prediction", "quantum", "benchmark", "input_metrics"):
                self.assertIn(key, result)

    def test_upload_prediction_and_validation_errors(self):
        body, headers = self.multipart(FIXTURE.name, FIXTURE.read_bytes())
        status, _, result = self.call("/api/v1/predict/upload", method="POST", body=body, headers=headers)
        self.assertEqual(status, 200, result)
        self.assertEqual(result["source"]["type"], "upload")
        body, headers = self.multipart("genome.fna", b">seq\nACGT\n")
        status, _, error = self.call("/api/v1/predict/upload", method="POST", body=body, headers=headers)
        self.assertEqual(status, 400)
        self.assertIn(".rna_seq.augmented_star_gene_counts.tsv", error["detail"])
        self.assertEqual(error["detail"], error["error"])

    def test_unknown_routes_and_samples_are_404(self):
        status, _, error = self.call("/api/v1/predict/demo/NOPE", method="POST", body=b"{}")
        self.assertEqual(status, 404)
        self.assertEqual(error["detail"], "Unknown demo sample.")
        self.assertEqual(self.call("/api/v1/missing")[0], 404)

    def test_cors_only_echoes_allowed_origins(self):
        status, headers, _ = self.call("/api/v1/health", headers={"Origin": ALLOWED_ORIGIN})
        self.assertEqual(headers["Access-Control-Allow-Origin"], ALLOWED_ORIGIN)
        _, headers, _ = self.call("/api/v1/health", headers={"Origin": "https://evil.example"})
        self.assertIsNone(headers["Access-Control-Allow-Origin"])
        status, headers, _ = self.call("/api/v1/predict/upload", method="OPTIONS", headers={"Origin": ALLOWED_ORIGIN})
        self.assertEqual(status, 204)
        self.assertIn("POST", headers["Access-Control-Allow-Methods"])


if __name__ == "__main__":
    unittest.main()
