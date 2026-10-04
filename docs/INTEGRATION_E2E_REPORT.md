# Integration E2E report

Date: 2026-09-30

## Environment

- Backend: `backend/quantum_test/Scripts/python.exe`
- Frontend: Vite on `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`

## Results

- Frontend loaded successfully.
- Backend reported `ready` with `models_loaded: true`.
- Catalog displayed 15 samples.
- Primary Tumor filter displayed 8 samples.
- Solid Tissue Normal filter displayed 7 samples.
- Random selection completed.
- Normal demo inference completed for `BRCA-DEMO-009`.
- Tumor demo inference completed for `BRCA-DEMO-001`.
- Complete raw TSV upload completed for `BRCA-DEMO-001`.
- Eight biomarkers appeared in locked order.
- Logistic, Candidate A, and A/E results appeared.
- Agreement, timing, lock fingerprint, and research disclaimer appeared.
- Invalid `.fna` upload returned a readable suffix validation error.
- Browser console errors: none observed.
- Failed network requests: none observed.

The immutable model-lock SHA-256 remained `1a4f71c7b619297537068f7dfd37c12a1725d56f5d5a80f9b24125421689f50a`.
