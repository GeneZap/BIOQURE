import React from "react";

function firstDefined(...values) {
  return values.find(
    (value) =>
      value !== undefined &&
      value !== null &&
      value !== ""
  );
}

function formatPercent(value) {
  if (
    value === undefined ||
    value === null ||
    value === ""
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return String(value);
  }

  const percentage =
    number >= 0 && number <= 1
      ? number * 100
      : number;

  return `${percentage.toFixed(1)}%`;
}

function MetricCard({
  label,
  value,
  description,
}) {
  return (
    <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-4">
      <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
        {label}
      </div>

      <div className="mt-2 break-words text-lg font-extrabold text-[var(--bq-text)]">
        {value ?? "—"}
      </div>

      {description && (
        <div className="mt-1 text-xs leading-5 text-[var(--bq-text-dim)]">
          {description}
        </div>
      )}
    </div>
  );
}

export default function ReportMetrics({
  analysis,
  dataset,
}) {
  const prediction = firstDefined(
    analysis?.prediction?.label,
    analysis?.prediction?.class_label,
    analysis?.prediction?.prediction,
    analysis?.predicted_label,
    analysis?.predicted_class,
    analysis?.label,
    typeof analysis?.prediction === "string"
      ? analysis.prediction
      : null
  );

  const confidence = firstDefined(
    analysis?.prediction?.probability,
    analysis?.prediction?.confidence,
    analysis?.prediction?.score,
    analysis?.probability,
    analysis?.confidence,
    analysis?.score
  );

  const selectedModel = firstDefined(
    analysis?.model_selection?.selected_model,
    analysis?.model_selection?.model,
    analysis?.selected_model,
    analysis?.model,
    analysis?.inference?.selected_model
  );

  const quantumUsed = firstDefined(
    analysis?.quantum?.used,
    analysis?.quantum_used,
    analysis?.runtime?.quantum_used,
    analysis?.inference?.quantum_used
  );

  const fallbackUsed = firstDefined(
    analysis?.fallback_used,
    analysis?.runtime?.fallback_used,
    analysis?.inference?.fallback_used
  );

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Prediction"
        value={prediction || "—"}
        description="Returned model classification"
      />

      <MetricCard
        label="Confidence"
        value={formatPercent(confidence)}
        description="Reported inference probability"
      />

      <MetricCard
        label="Selected model"
        value={selectedModel || "—"}
        description="Model selected from validation metadata"
      />

      <MetricCard
        label="Quantum path"
        value={
          quantumUsed === true
            ? "Used"
            : quantumUsed === false
              ? "Not used"
              : "—"
        }
        description={
          fallbackUsed === true
            ? "Classical fallback was used"
            : dataset?.id
              ? `Dataset: ${dataset.id}`
              : "Runtime quantum status"
        }
      />
    </div>
  );
}