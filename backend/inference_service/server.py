"""Dependency-light HTTP API and static frontend server."""

from __future__ import annotations

from email import policy
from email.parser import BytesParser
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import random
import os
import sys
import uuid
from urllib.parse import unquote

from .inference import ALLOWED_SUFFIX, MAX_UPLOAD_BYTES, InferenceError, LockedInferenceEngine


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
ENGINE = LockedInferenceEngine()
FIRST_PARTY_CORS_ORIGINS = {
    "https://bioqure.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}
CORS_ORIGINS = FIRST_PARTY_CORS_ORIGINS | {
    origin.strip().rstrip("/")
    for origin in os.getenv("BIOQURE_CORS_ORIGINS", "").split(",")
    if origin.strip()
}


class Handler(BaseHTTPRequestHandler):
    server_version = "BioQureInference/1.0"

    def _cors(self) -> None:
        origin = self.headers.get("Origin", "").rstrip("/")
        if origin in CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-ID")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("X-Request-ID", self.headers.get("X-Request-ID", str(uuid.uuid4())))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            raise InferenceError(f"Upload must be between 1 byte and {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        return self.rfile.read(length)

    def do_GET(self) -> None:
        try:
            if self.path == "/api/v1/health":
                self._json(200, {"status": "ready", "state": "ready", "model_lock_sha256": ENGINE.lock_hash, "models_loaded": True})
            elif self.path == "/api/v1/model-info":
                self._json(200, ENGINE.model_info())
            elif self.path == "/api/v1/demo-samples":
                self._json(200, {"samples": ENGINE.demo_list()})
            elif self.path.startswith("/api/v1/demo-samples/") and self.path.endswith("/download"):
                sample_id = unquote(self.path[len("/api/v1/demo-samples/") : -len("/download")])
                item = ENGINE.demo_samples.get(sample_id)
                if item is None:
                    raise InferenceError("Unknown demo sample.")
                fixture = ROOT / item["fixture_path"]
                body = fixture.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/tab-separated-values; charset=utf-8")
                self._cors()
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{sample_id}{ALLOWED_SUFFIX}"',
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/" or self.path == "/index.html":
                body = (WEB_ROOT / "index.html").read_bytes()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif self.path in ("/app.js", "/styles.css"):
                path = WEB_ROOT / self.path.lstrip("/")
                body = path.read_bytes()
                content_type = "text/javascript; charset=utf-8" if path.suffix == ".js" else "text/css; charset=utf-8"
                self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            else:
                self._json(404, {"error": "Not found"})
        except Exception as error:
            self._json(500, {"error": str(error)})

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self) -> None:
        try:
            if self.path.startswith("/api/v1/predict/demo/"):
                sample_id = unquote(self.path.rsplit("/", 1)[-1])
                item = ENGINE.demo_samples.get(sample_id)
                if item is None:
                    raise InferenceError("Unknown demo sample.")
                fixture = ROOT / item["fixture_path"]
                result = ENGINE.infer(fixture.read_bytes(), "demo", item["display_name"], item.get("sample_type"))
                self._json(200, result)
                return
            if self.path == "/api/v1/predict/upload":
                if not self.headers.get("Content-Type", "").startswith("multipart/form-data"):
                    raise InferenceError("Upload must use multipart/form-data.")
                if int(self.headers.get("Content-Length", "0")) > MAX_UPLOAD_BYTES:
                    raise InferenceError("Upload exceeds the configured 25 MB limit.")
                body = self._body()
                message = BytesParser(policy=policy.default).parsebytes(
                    b"Content-Type: " + self.headers["Content-Type"].encode("ascii") + b"\r\n\r\n" + body
                )
                field = next(
                    (part for part in message.iter_attachments() if part.get_param("name", header="content-disposition") == "file"),
                    None,
                )
                if field is None or not field.get_filename():
                    raise InferenceError("Choose one STAR-counts TSV file.")
                filename = Path(field.get_filename()).name
                if not filename.endswith(ALLOWED_SUFFIX):
                    raise InferenceError(f"File must end with {ALLOWED_SUFFIX}.")
                content = field.get_payload(decode=True) or b""
                if len(content) > MAX_UPLOAD_BYTES:
                    raise InferenceError("Upload exceeds the configured 25 MB limit.")
                self._json(200, ENGINE.infer(content, "upload", filename))
                return
            self._json(404, {"error": "Not found"})
        except InferenceError as error:
            self._json(400, {"error": str(error)})
        except Exception as error:
            self._json(500, {"error": str(error)})


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    print(f"BioQure inference server: http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
