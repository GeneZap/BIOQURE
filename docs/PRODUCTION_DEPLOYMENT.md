# Production deployment

The repository includes a Render Blueprint in `render.yaml` with:

- `bioqure-inference`: persistent Docker web service using the locked Python/Qiskit runtime;
- `bioqure-frontend`: static frontend built from `frontend/`.

Deploy the Blueprint from the `chore/finalize-production-packaging` branch or after
merging its packaging PR. Render must be authorized to access the repository and the
Blueprint must be reviewed before creation. The configured environment values are:

- `BIOQURE_CORS_ORIGINS=https://bioqure-frontend.onrender.com`
- `VITE_API_BASE_URL=https://bioqure-inference.onrender.com`

After deployment, verify `/api/v1/health`, `/api/v1/model-info`, `/api/v1/demo-samples`,
one normal demo, one tumor demo, one raw TSV upload, and one invalid upload. Do not report
deployment success until those public HTTPS checks and the frontend browser flow pass.

This is a research demonstration only. The output is not a medical diagnosis and must not
be used for clinical decisions.