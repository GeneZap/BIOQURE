# BIOQURE integration architecture

The React/Vite application in `frontend/` calls the authoritative Python service in
`backend/inference_service/`. The service loads the immutable model lock, verifies
artifact hashes once at startup, resolves public IDs through `backend/public_dataset_pool/`,
and owns all parsing, preprocessing, classical inference, and quantum ensembles.

`BIOQURE_BACKEND-main/` is not part of this integration because the frontend did not
reference it. Public samples send only a `demo_id`; local files use multipart upload.