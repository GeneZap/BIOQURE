import React from "react";

function firstDefined(...values) {
  return values.find(
    (value) =>
      value !== undefined &&
      value !== null &&
      value !== ""
  );
}

function formatNumber(value) {
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

  return new Intl.NumberFormat("en-IN").format(number);
}

function formatDuration(value) {
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

  if (number < 1000) {
    return `${number.toFixed(0)} ms`;
  }

  return `${(number / 1000).toFixed(2)} s`;
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
        {value}
      </div>

      {description && (
        <div className="mt-1 text-xs leading-5 text-[var(--bq-text-dim)]">
          {description}
        </div>
      )}
    </div>
  );
}

function InfoRow({
  label,
  value,
}) {
  return (
    <div className="flex flex-col gap-1 border-b border-[var(--bq-border)] py-3 last:border-b-0 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <span className="text-xs font-medium text-[var(--bq-text-dim)]">
        {label}
      </span>

      <span className="break-all text-xs font-bold text-[var(--bq-text)] sm:text-right">
        {value ?? "—"}
      </span>
    </div>
  );
}

export default function ReportInputMetrics({
  analysis,
  dataset,
}) {
  const preprocessing =
    analysis?.preprocessing ??
    analysis?.preprocessing_metadata ??
    {};

  const input =
    analysis?.input ??
    analysis?.input_metrics ??
    {};

  const runtime =
    analysis?.runtime ??
    {};

  const sampleCount = firstDefined(
    dataset?.sampleCount,
    dataset?.sample_count,
    input?.sample_count,
    input?.samples,
    preprocessing?.sample_count
  );

  const geneCount = firstDefined(
    dataset?.geneCount,
    dataset?.gene_count,
    input?.gene_count,
    input?.genes,
    preprocessing?.gene_count
  );

  const featureCount = firstDefined(
    input?.feature_count,
    preprocessing?.feature_count,
    preprocessing?.n_features
  );

  const selectedFeatureCount = firstDefined(
    input?.selected_feature_count,
    preprocessing?.selected_feature_count
  );

  const missingFeatureCount = firstDefined(
    input?.missing_feature_count,
    preprocessing?.missing_feature_count,
    preprocessing?.missing_features_count
  );

  const preprocessingTime = firstDefined(
    runtime?.preprocessing_time_ms,
    runtime?.preprocess_time_ms,
    preprocessing?.duration_ms,
    analysis?.timing_ms?.preprocessing
  );

  const inferenceTime = firstDefined(
    runtime?.inference_time_ms,
    runtime?.prediction_time_ms,
    runtime?.duration_ms,
    analysis?.timing_ms?.quantum_inference
  );

  const totalTime = firstDefined(
    runtime?.total_time_ms,
    runtime?.elapsed_ms,
    analysis?.elapsed_ms,
    analysis?.timing_ms?.total
  );

  const transform = firstDefined(
    preprocessing?.transform,
    preprocessing?.transformation,
    preprocessing?.normalization
  );

  const featureSelection = firstDefined(
    preprocessing?.feature_selection,
    preprocessing?.selected_features,
    preprocessing?.feature_names
  );

  const scaler = firstDefined(
    preprocessing?.scaler,
    preprocessing?.scaling,
    preprocessing?.normalization_method
  );

  const sourceFile = firstDefined(
    dataset?.fileName,
    dataset?.filename,
    dataset?.expression_file,
    input?.source_file,
    input?.filename
  );

  const datasetId = firstDefined(
    dataset?.id,
    dataset?.dataset_id,
    input?.dataset_id
  );

  const project = firstDefined(
    dataset?.project,
    dataset?.project_id,
    input?.project
  );

  return (
    <div className="space-y-5">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-black text-[var(--bq-text)]">
            Input dataset metrics
          </h3>

          <span className="inline-flex items-center rounded-full border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] px-2.5 py-1 text-[11px] font-semibold text-[var(--bq-text-dim)]">
            PREPROCESSING
          </span>
        </div>

        <p className="mt-1 max-w-3xl text-sm leading-6 text-[var(--bq-text-dim)]">
          Dataset and preprocessing metadata associated with the
          BIOQURE inference request.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Dataset"
          value={datasetId || "—"}
          description="BIOQURE dataset identifier"
        />

        <MetricCard
          label="Samples"
          value={formatNumber(sampleCount)}
          description="Reported input sample count"
        />

        <MetricCard
          label="Raw gene rows parsed"
          value={formatNumber(geneCount)}
          description="Non-summary STAR-counts rows found in the uploaded TSV"
        />

        <MetricCard
          label="Selected features"
          value={formatNumber(
            selectedFeatureCount ?? featureCount
          )}
          description="Locked biomarkers actually passed into each model"
        />
      </div>

      <div>
        <div className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
          Preprocessing
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Transformation"
            value={transform || "Not reported"}
            description="Expression transformation"
          />

          <MetricCard
            label="Scaler"
            value={scaler || "—"}
            description="Training-compatible scaling"
          />

          <MetricCard
            label="Missing features"
            value={formatNumber(
              missingFeatureCount
            )}
            description="Features not found in input"
          />

          <MetricCard
            label="Project"
            value={project || "—"}
            description="Dataset project identifier"
          />
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-5">
          <div className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
            Dataset metadata
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface)] px-4">
            <InfoRow
              label="Dataset ID"
              value={datasetId}
            />

            <InfoRow
              label="Source"
              value={dataset?.source}
            />

            <InfoRow
              label="Project"
              value={project}
            />

            <InfoRow
              label="Data type"
              value={dataset?.dataType}
            />

            <InfoRow
              label="Expression file"
              value={sourceFile}
            />

            <InfoRow
              label="Access"
              value={dataset?.access}
            />
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-5">
          <div className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
            Preprocessing metadata
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface)] px-4">
            <InfoRow
              label="Transformation"
              value={transform || "Not reported"}
            />

            <InfoRow
              label="Scaler"
              value={scaler}
            />

            <InfoRow
              label="Feature count"
              value={formatNumber(featureCount)}
            />

            <InfoRow
              label="Selected feature count"
              value={formatNumber(
                selectedFeatureCount
              )}
            />

            <InfoRow
              label="Missing feature count"
              value={formatNumber(
                missingFeatureCount
              )}
            />
          </div>
        </div>
      </div>

      {Array.isArray(featureSelection) &&
        featureSelection.length > 0 && (
          <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-5">
            <div className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
              Features used by inference
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {featureSelection.map(
                (feature, index) => (
                  <span
                    key={`${feature}-${index}`}
                    className="rounded-lg border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] px-2.5 py-1.5 font-mono text-[11px] font-semibold text-[var(--bq-text)]"
                  >
                    {typeof feature === "string"
                      ? feature
                      : JSON.stringify(feature)}
                  </span>
                )
              )}
            </div>
          </div>
        )}

      <div>
        <div className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
          Runtime timings
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <MetricCard
            label="Preprocessing"
            value={formatDuration(
              preprocessingTime
            )}
            description="Reported preprocessing duration"
          />

          <MetricCard
            label="Inference"
            value={formatDuration(
              inferenceTime
            )}
            description="Reported model inference duration"
          />

          <MetricCard
            label="Total"
            value={formatDuration(totalTime)}
            description="Reported total request duration"
          />
        </div>
      </div>

      <details className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)]">
        <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-[var(--bq-text-dim)]">
          View complete input/preprocessing payload
        </summary>

        <div className="grid gap-4 border-t border-[var(--bq-border)] p-4 lg:grid-cols-2">
          <div>
            <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--bq-text-faint)]">
              Input
            </div>

            <pre className="max-h-[400px] overflow-auto rounded-xl bg-[#05080c] p-4 text-[10px] leading-5 text-[var(--bq-text-dim)]">
              {JSON.stringify(
                input,
                null,
                2
              )}
            </pre>
          </div>

          <div>
            <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--bq-text-faint)]">
              Preprocessing
            </div>

            <pre className="max-h-[400px] overflow-auto rounded-xl bg-[#05080c] p-4 text-[10px] leading-5 text-[var(--bq-text-dim)]">
              {JSON.stringify(
                preprocessing,
                null,
                2
              )}
            </pre>
          </div>
        </div>
      </details>
    </div>
  );
}
