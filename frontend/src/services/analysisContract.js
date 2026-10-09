/**
 * Read the locked BIOQURE inference response in one place.
 *
 * The production API exposes the deployment result under
 * `deployment_prediction`; older development responses used the generic
 * `prediction`/`confidence` fields.  Keeping both forms here prevents report
 * panels from silently drifting away from the backend contract again.
 */

export function firstDefined(...values) {
  return values.find(
    (value) => value !== undefined && value !== null && value !== "",
  );
}

export function getDeploymentPrediction(analysis) {
  return (
    analysis?.deployment_prediction ??
    analysis?.predictions?.classical_logistic ??
    null
  );
}

export function getPrediction(analysis) {
  const deployment = getDeploymentPrediction(analysis);
  const legacy = firstDefined(
    analysis?.prediction,
    analysis?.result?.prediction,
    analysis?.classification,
  );

  if (deployment?.predicted_class) return deployment.predicted_class;
  if (typeof legacy === "string") return legacy;

  return firstDefined(
    legacy?.label,
    legacy?.class_label,
    legacy?.prediction,
    analysis?.predicted_label,
    analysis?.predicted_class,
    analysis?.label,
    "—",
  );
}

export function getTumorProbability(analysis) {
  const deployment = getDeploymentPrediction(analysis);
  const legacy = firstDefined(
    analysis?.prediction,
    analysis?.result?.prediction,
  );

  return firstDefined(
    deployment?.tumor_probability,
    legacy?.probability,
    legacy?.confidence,
    legacy?.score,
    analysis?.probability,
    analysis?.confidence,
    analysis?.score,
  );
}

export function getSelectedModel(analysis) {
  return firstDefined(
    analysis?.benchmark?.selected_model_label,
    getDeploymentPrediction(analysis)?.model,
    analysis?.benchmark?.selected_model,
    analysis?.model_selection?.selected_model,
    analysis?.model_selection?.model,
    analysis?.selected_model,
    analysis?.model,
    analysis?.inference?.selected_model,
    "—",
  );
}

export function getQuantumUsed(analysis) {
  return firstDefined(
    analysis?.quantum?.used,
    analysis?.quantum_used,
    analysis?.runtime?.quantum_used,
    analysis?.inference?.quantum_used,
  );
}

export function getFallbackUsed(analysis) {
  return firstDefined(
    analysis?.quantum?.fallback_used,
    analysis?.fallback_used,
    analysis?.runtime?.fallback_used,
    analysis?.inference?.fallback_used,
  );
}

export function getBiomarkers(analysis, limit) {
  const source =
    analysis?.biomarkers ??
    analysis?.biomarker_summary ??
    analysis?.result?.biomarkers ??
    [];

  const rows = Array.isArray(source)
    ? source
    : Object.entries(source || {}).map(([gene, value]) => ({ gene, value }));

  const normalized = rows.map((item, index) => ({
    ...item,
    gene: firstDefined(
      item?.gene,
      item?.gene_name,
      item?.feature,
      item?.name,
      `Feature ${index + 1}`,
    ),
    value: firstDefined(
      item?.log2_tpm_plus_1,
      item?.raw_tpm,
      item?.value,
      item?.expression,
      item?.score,
      item?.importance,
      item?.signal,
    ),
  }));

  return Number.isInteger(limit) ? normalized.slice(0, limit) : normalized;
}
