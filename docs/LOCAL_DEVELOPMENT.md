# Local development

Install the pinned backend dependencies with `python -m pip install -r backend/requirements-runtime.txt`.
Start the service from `backend/` with `python -m inference_service.server 8000`, then run
the frontend from `frontend/` with `npm ci` and `npm run dev`.

Set `VITE_API_BASE_URL` to the backend origin when it is not `http://localhost:8000`.
Set `BIOQURE_CORS_ORIGINS` to a comma-separated list of allowed browser origins.