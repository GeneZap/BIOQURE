# Public dataset pool

`backend/scripts/build_public_dataset_pool.py` uses seed 42 and the leakage-safe split
manifest to select exactly seven Primary Tumor and eight Solid Tissue Normal training
samples. The catalog records anonymous IDs, sample type, training split, source alias,
file size, biomarker availability, and SHA-256. It does not contain synthetic quality
scores.

Raw files remain server-side. `POST /api/v1/predict/demo/{demo_id}` resolves the catalog
entry and sends its contents through the locked parser and models.
