# BioQure

BioQure is a research-only breast-cancer expression demonstration using a locked classical and quantum inference pipeline.

## Production surfaces

- `backend/inference_service/`: hash-verified inference API.
- `backend/runtime/`: copied locked models, scalers, and runtime manifest.
- `backend/public_dataset_pool/`: 15 server-side training-split GDC STAR-count samples.
- `frontend/`: Vite/React research console.
- `docs/`: integration, deployment, and validation documentation.

The service exposes:

- `GET /api/v1/health`
- `GET /api/v1/model-info`
- `GET /api/v1/demo-samples`
- `POST /api/v1/predict/demo/{demo_id}`
- `POST /api/v1/predict/upload`

The locked feature order is `FABP4`, `LEP`, `COL10A1`, `CHRDL1`, `SCARA5`, `SAA1`, `SFRP1`, `LPL`. The immutable lock SHA-256 is:

`1a4f71c7b619297537068f7dfd37c12a1725d56f5d5a80f9b24125421689f50a`

The fingerprint is computed over the lock JSON with line endings normalised to CRLF, so it is identical on Windows, Linux and Docker checkouts. The service refuses to start if it differs.

## Local development

Install the pinned backend dependencies from `backend/requirements-runtime.txt`. Start the backend with Python 3.13 and run the frontend with `npm ci` followed by `npm run dev` in `frontend/`. Set `VITE_API_BASE_URL` for the frontend and `BIOQURE_CORS_ORIGINS` for the backend.

## Deployment

The portable Render configuration is in `render.yaml`. The Dockerfile builds only the locked inference service and its production artifacts. See [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md).

Research demonstration only. This output is not a medical diagnosis and must not be used for clinical decisions.
