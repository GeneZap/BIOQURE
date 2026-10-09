import React from "react";
import {
  getFallbackUsed,
  getPrediction,
  getQuantumUsed,
  getSelectedModel,
  getTumorProbability,
} from "../../services/analysisContract.js";

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
  const prediction = getPrediction(analysis);
  const confidence = getTumorProbability(analysis);
  const selectedModel = getSelectedModel(analysis);
  const quantumUsed = getQuantumUsed(analysis);
  const fallbackUsed = getFallbackUsed(analysis);

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Prediction"
        value={prediction || "—"}
        description="Returned model classification"
      />

      <MetricCard
        label="Tumor probability"
        value={formatPercent(confidence)}
        description="Deployment endpoint probability; not clinical certainty"
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
