# Research pipeline → locked runtime mapping

The research and training code lives in
[GeneZap/BIOQURE_BACKEND](https://github.com/GeneZap/BIOQURE_BACKEND). This repository
holds only the hash-verified artifacts that pipeline produced, plus the inference
service that loads them. Nothing here retrains or refits. The lock
(`backend/configs/final_model_lock.json`) remains the source of truth.

| Stage | BIOQURE_BACKEND script | Output used by the locked runtime |
| --- | --- | --- |
| 1. GDC metadata | `metadata extraction/build_gdc_sample_metadata.py` | `gdc_sample_metadata.csv` (file → case, sample type) |
| 2. Expression matrix | `expression_matrix/merge_gdc_expression_matrix.py` | `tpm_unstranded` → `log2(TPM + 1)` matrix. Same transform as `inference_service.inference.parse_star_counts` + `log2(x + 1)` |
| 3. Biomarkers and splits | `expression_matrix/select_biomarkers_leakage_safe.py` | Patient-grouped train/validation/test split and the 8 genes, chosen using training samples only: `FABP4, LEP, COL10A1, CHRDL1, SCARA5, SAA1, SFRP1, LPL` (`FEATURE_NAMES`) |
| 4. Scaling | `TRAINING_QUANTUM/prepare_model_data.py` | `runtime/model_artifacts/scalers/classical_scaler.joblib` (StandardScaler) and `quantum_scaler.joblib` (MinMaxScaler), both fitted on the training split. Settings recorded in `runtime/config/preparation_config.json` |
| 5. Training | `TRAINING_QUANTUM/train_hybrid_models.py` | `logistic_regression.joblib` and one `vqc_model.dill` per seed, copied to `runtime/model_artifacts/{classical,candidate_a,candidate_e}/` |
| 6. Analysis | `analyze_vqc_results.py` | Validation comparison used to pick Candidates A and E. Their validation metrics are in the lock |
| 7. Packaging | `backend/scripts/build_runtime_bundle.py` (this repo) | Copies the artifacts and records original and copied SHA-256s in `runtime/config/runtime_model_manifest.json` |

## Locked configurations

- **Logistic regression** (primary): from `training_outputs/angle_screen_zero_half_pi_seed21/`. Tumor if p ≥ 0.50.
- **Candidate A** (quantum): `zz_feature_map` reps 1, `real_amplitudes` reps 2, linear entanglement,
  COBYLA maxiter 300, 2048 shots, seeds 7/21/42/84/126
  (`angle_screen_zero_half_pi_seed*`). Uses the mean of the five seeds; Tumor if ≥ 0.33.
- **Candidate E**: same, but `zz_feature_map` reps 2 and `real_amplitudes` reps 1
  (`architecture_screen_zero_half_pi_E_seed*`).
- **A/E balanced**: `0.55 × median(A) + 0.45 × median(E)`. Tumor if ≥ 0.34.

## Known divergence

The locked bundle uses quantum angles in **[0, π/2]** (`quantum_angle_range: zero-half-pi`,
quantum majority ratio 1.0). The committed `prepare_model_data.py` still hard-codes
`MinMaxScaler(feature_range=(0.0, np.pi))`. Re-running it unchanged therefore will **not**
reproduce the locked quantum scaler. The `angle_screen_zero_half_pi_*` runs were produced with a
`[0, π/2]` variant that is not committed. Any retraining must restore that variant and goes
through a new lock. It must never be patched into this runtime.

`train_hybrid_models.py --evaluate-test` reveals held-out test metrics. The lock records
`test_set_status` as not yet evaluated. The report's `benchmark` section therefore shows
validation metrics only.
