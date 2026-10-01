# Public dataset pool

`backend/scripts/build_public_dataset_pool.py` uses seed 42 and the leakage-safe split
manifest to select exactly eight Primary Tumor and seven Solid Tissue Normal training
samples. The catalog contains anonymous IDs, type, split, size, and SHA-256 only.

Raw files remain server-side. `POST /api/v1/predict/demo/{demo_id}` resolves the catalog
entry and sends its contents through the locked parser and models.