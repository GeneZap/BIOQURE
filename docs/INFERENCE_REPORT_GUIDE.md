# BIOQURE inference report guide

BIOQURE is a research prototype. Its outputs are model scores, not diagnoses or
clinical confidence estimates.

## Per-sample outputs

- **Classical logistic regression** is the locked deployment endpoint. Its
  `tumor_probability` is the fitted model probability and its decision threshold
  is `0.50`.
- **Candidate A** is an arithmetic mean of five VQC probabilities trained with
  seeds `7, 21, 42, 84, 126`. Candidate A uses a one-repetition ZZ feature map,
  a two-repetition RealAmplitudes ansatz, and threshold `0.33`.
- **Candidate E** is a second five-seed VQC architecture. It uses a
  two-repetition ZZ feature map and a one-repetition RealAmplitudes ansatz.
- **A/E balanced** is not Candidate E alone. It is
  `0.55 * median(Candidate A seeds) + 0.45 * median(Candidate E seeds)`, with
  threshold `0.34`.

The report exposes the seed probabilities and component medians so the ensemble
calculation can be audited.

## Biomarker values

The eight locked biomarkers are shown in their fixed model order:

`FABP4, LEP, COL10A1, CHRDL1, SCARA5, SAA1, SFRP1, LPL`

For each gene the report displays raw TPM, `log2(TPM + 1)`, the value supplied to
the classical model after scaling, and the quantum rotation angle. These values
are model inputs; they are not feature-importance or causal-effect estimates.

## Benchmark values

ROC-AUC, balanced accuracy, sensitivity, specificity, MCC, and Brier scores are
copied from the immutable model lock. They summarize the saved validation run;
they are not recalculated for the selected demo sample. The held-out test set
remains unevaluated.

“Quantum operating constraints passed” means only that the saved A/E validation
sensitivity was at least `0.80` and specificity was at least `0.70`. It does not
mean quantum outperformed the classical baseline. Logistic regression remains
the locked deployment endpoint.

## Demo-pool integrity

Demo labels must come from GDC sample metadata joined to the training split
manifest. The server rejects catalogs without verified label provenance, files
outside the training split, hash mismatches, malformed STAR-counts files, or a
class balance other than eight tumors and seven normals. Do not assign labels
from filenames, list positions, or model predictions.
