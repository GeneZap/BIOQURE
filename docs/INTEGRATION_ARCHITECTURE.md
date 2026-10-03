# BIOQURE integration architecture

The React/Vite application in `frontend/` calls the authoritative Python service in
`backend/inference_service/`. The service loads the immutable model lock, verifies
artifact hashes once at startup, resolves public IDs through `backend/public_dataset_pool/`,
and owns all parsing, preprocessing, classical inference, and quantum ensembles.

`BIOQURE_BACKEND-main/` is not part of this integration because the frontend did not
reference it. Public samples send only a `demo_id`; local files use multipart upload.

## Prediction response

`POST /api/v1/predict/demo/{demo_id}` and `POST /api/v1/predict/upload` return the
authoritative locked fields (`predictions`, `biomarkers`, `agreement`, `timing_ms`,
`model_lock`) plus report sections derived from them in
`backend/inference_service/report.py` for the frontend report tabs:

- `prediction`: the locked logistic-regression decision (primary endpoint).
- `classical_models`: the logistic-regression endpoint with its validation metrics.
- `quantum`: the Candidate A ensemble, its circuit, shots, per-seed probabilities,
  per-qubit angles and the Candidate A/E balanced endpoint.
- `benchmark`: validation-split metrics from the model lock for all three endpoints and
  this request's inference time. The held-out test set has not been evaluated.
- `input_metrics`: genes detected in the file and the eight locked biomarker values.

Biomarker `importance` is the normalised absolute logistic coefficient. Report sections
never change locked probabilities, thresholds or decisions.

Errors are JSON `{"error": message, "detail": message}` with status 400 (invalid input),
404 (unknown route or demo ID) or 500. `GET` endpoints also answer `HEAD`, and `GET /`
returns the health payload.
