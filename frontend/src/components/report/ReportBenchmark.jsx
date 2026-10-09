import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Gauge,
  ShieldCheck,
  XCircle,
} from 'lucide-react'

function clamp01(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return null
  return Math.min(1, Math.max(0, number))
}

function formatPercent(value, digits = 1) {
  const number = clamp01(value)
  return number == null ? '—' : `${(number * 100).toFixed(digits)}%`
}

function formatScore(value, digits = 3) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(digits) : '—'
}

function modelDisplayName(key, model = {}) {
  if (model?.name) return model.name

  const names = {
    logistic_regression: 'Logistic Regression',
    rbf_svm: 'RBF-SVM',
    xgboost: 'XGBoost',
    mlp: 'MLP',
    vqc: 'VQC',
    classical_logistic: 'Classical logistic regression',
    quantum_candidate_a_mean: 'Candidate A five-seed mean ensemble',
    quantum_ae_balanced: 'A/E balanced quantum ensemble',
  }

  return names[key] || key
}

function outcomeLabel(outcome) {
  switch (String(outcome || '').toLowerCase()) {
    case 'hybrid':
      return 'Hybrid decision'
    case 'classical_fallback':
      return 'Classical fallback'
    case 'vqc':
      return 'Quantum model selected'
    case 'classical':
      return 'Classical model selected'
    default:
      return outcome || 'Not available'
  }
}

function CheckCard({ label, passed, description }) {
  return (
    <div
      className={[
        'rounded-2xl border p-4',
        passed ? 'border-emerald-400/30 bg-emerald-400/10' : 'border-rose-400/30 bg-rose-400/10',
      ].join(' ')}
    >
      <div className="flex items-start gap-3">
        <div
          className={[
            'mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl',
            passed ? 'bg-emerald-400/15' : 'bg-rose-400/15',
          ].join(' ')}
        >
          {passed ? (
            <CheckCircle2 className="size-5 text-emerald-300" aria-hidden />
          ) : (
            <XCircle className="size-5 text-rose-300" aria-hidden />
          )}
        </div>

        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--bq-text)]">{label}</p>

          <p
            className={[
              'mt-1 text-xs font-bold uppercase tracking-wider',
              passed ? 'text-emerald-300' : 'text-rose-300',
            ].join(' ')}
          >
            {passed ? 'Passed' : 'Not passed'}
          </p>

          {description && (
            <p className="mt-2 text-xs leading-relaxed text-[var(--bq-text-dim)]">{description}</p>
          )}
        </div>
      </div>
    </div>
  )
}

function MetricCell({ value, percentage = false }) {
  return (
    <span className="font-mono text-xs tabular-nums text-[var(--bq-text)]">
      {percentage ? formatPercent(value) : formatScore(value)}
    </span>
  )
}

export default function ReportBenchmark({ analysis = null }) {
  const result = analysis || {}
  const benchmark = result?.benchmark ?? result?.benchmark_summary ?? {}

  const models = benchmark?.models || {}
  const checks = benchmark?.checks || {}
  const calibration = benchmark?.calibration || {}
  const predictions = result?.predictions || {}
  const deployment = result?.deployment_prediction || {}

  const modelEntries = Object.entries(models)

  const selectedModel =
    deployment?.model ??
    result?.prediction?.selected_model ??
    result?.selected_model ??
    benchmark?.selected_model ??
    null

  const bestClassical =
    benchmark?.best_classical_model ?? result?.selection?.best_classical_model ?? null

  const outcome = outcomeLabel(
    benchmark?.outcome ?? result?.selection?.outcome ?? result?.prediction?.selected_model
  )

  const robustness = checks?.quantum_robust === true || checks?.robust === true

  const improves = checks?.quantum_improves === true || checks?.improves === true

  const calibrationMetric = calibration?.metric || calibration?.name || 'Calibration'

  const quantumCalibration =
    calibration?.quantum_candidate_a ??
    calibration?.quantum_ae_balanced ??
    calibration?.quantum ??
    calibration?.vqc ??
    calibration?.quantum_brier_score

  const classicalCalibration =
    calibration?.classical_baseline ?? calibration?.classical ?? calibration?.classical_brier_score

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl border border-violet-400/30 bg-violet-400/10">
            <Gauge className="size-5 text-violet-300" aria-hidden />
          </div>

          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--bq-text-faint)]">
              Benchmark & decision
            </p>
            <h2 className="mt-1 text-xl font-bold tracking-tight text-[var(--bq-text)]">
              Classical vs quantum evaluation
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[var(--bq-text-dim)]">
              Validation metrics, calibration information, and the model
              selection checks used by the BIOQURE decision layer.
            </p>
          </div>
        </div>

        <div className="shrink-0 rounded-full border border-violet-400/30 bg-violet-400/10 px-4 py-2 text-center">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-violet-400">
            Outcome
          </p>
          <p className="mt-0.5 text-sm font-bold text-violet-300">{outcome}</p>
        </div>
      </div>

      {/* Per-sample endpoint predictions */}
      <section className="overflow-hidden rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)]">
        <div className="border-b border-[var(--bq-border)] px-5 py-4">
          <h3 className="text-sm font-bold text-[var(--bq-text)]">Predictions for this sample</h3>
          <p className="mt-1 text-xs text-[var(--bq-text-dim)]">
            Candidate A and A/E share one locked quantum ensemble pass, so their reported quantum timing is shared.
          </p>
        </div>
        {Object.keys(predictions).length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left">
              <thead>
                <tr className="border-b border-[var(--bq-border)] bg-[var(--bq-surface-alt)]">
                  {['Model', 'Tumor probability', 'Threshold', 'Prediction', 'Inference'].map((heading) => (
                    <th key={heading} className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--bq-text-faint)]">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(predictions).map(([key, model]) => (
                  <tr key={key} className={`border-b border-[var(--bq-border)] last:border-b-0 ${key === selectedModel ? 'bg-violet-400/10' : ''}`}>
                    <td className="px-5 py-4 text-sm font-semibold text-[var(--bq-text)]">
                      {modelDisplayName(key, model)}
                      {key === selectedModel && (
                        <span className="ml-2 rounded-full border border-violet-400/30 px-2 py-1 text-[9px] uppercase text-violet-300">Deployment</span>
                      )}
                    </td>
                    <td className="px-5 py-4"><MetricCell value={model?.tumor_probability} percentage /></td>
                    <td className="px-5 py-4"><MetricCell value={model?.threshold} /></td>
                    <td className="px-5 py-4 text-xs font-semibold text-[var(--bq-text)]">{model?.predicted_class ?? '—'}</td>
                    <td className="px-5 py-4 text-xs text-[var(--bq-text-dim)]">
                      <span className="inline-flex items-center gap-1.5 font-mono">
                        <Clock3 className="size-3.5" aria-hidden />
                        {model?.inference_ms != null ? `${model.inference_ms} ms` : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-5 py-8 text-sm text-[var(--bq-text-dim)]">No endpoint predictions were returned.</div>
        )}
      </section>

      {/* Selection summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-5">
          <div className="flex items-center gap-2 text-[var(--bq-text-dim)]">
            <ShieldCheck className="size-4 text-violet-400" aria-hidden />
            <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
              Selected model
            </span>
          </div>

          <p className="mt-3 text-lg font-bold text-[var(--bq-text)]">
            {selectedModel || 'Not available'}
          </p>

          {bestClassical && (
            <p className="mt-1 text-xs text-[var(--bq-text-dim)]">
              Best classical baseline:{' '}
              <span className="font-semibold text-[var(--bq-text)]">{bestClassical}</span>
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-5">
          <div className="flex items-center gap-2 text-[var(--bq-text-dim)]">
            <CheckCircle2 className="size-4 text-emerald-400" aria-hidden />
            <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
              Quantum robustness
            </span>
          </div>

          <p
            className={[
              'mt-3 text-lg font-bold',
              robustness ? 'text-emerald-300' : 'text-rose-300',
            ].join(' ')}
          >
            {robustness ? 'Passed' : 'Not passed'}
          </p>

          <p className="mt-1 text-xs text-[var(--bq-text-dim)]">Based on the backend benchmark check.</p>
        </div>

        <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-5">
          <div className="flex items-center gap-2 text-[var(--bq-text-dim)]">
            <Gauge className="size-4 text-violet-400" aria-hidden />
            <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
              Quantum improvement
            </span>
          </div>

          <p
            className={[
              'mt-3 text-lg font-bold',
              improves ? 'text-emerald-300' : 'text-amber-300',
            ].join(' ')}
          >
            {improves ? 'Demonstrated' : 'Not demonstrated'}
          </p>

          <p className="mt-1 text-xs text-[var(--bq-text-dim)]">
            Compared with the validated classical baseline.
          </p>
        </div>
      </div>

      {/* Model comparison */}
      <section className="overflow-hidden rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)]">
        <div className="border-b border-[var(--bq-border)] px-5 py-4">
          <div className="flex items-center gap-2">
            <Gauge className="size-4 text-violet-400" aria-hidden />
            <h3 className="text-sm font-bold text-[var(--bq-text)]">Model comparison</h3>
          </div>

          <p className="mt-1 text-xs text-[var(--bq-text-dim)]">
            The same held-out benchmark should be used for every model shown here.
          </p>
        </div>

        {modelEntries.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left">
              <thead>
                <tr className="border-b border-[var(--bq-border)] bg-[var(--bq-surface-alt)]">
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--bq-text-faint)]">
                    Model
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--bq-text-faint)]">
                    Accuracy
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--bq-text-faint)]">
                    ROC-AUC
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--bq-text-faint)]">
                    Balanced accuracy
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--bq-text-faint)]">
                    Sensitivity
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--bq-text-faint)]">
                    Specificity
                  </th>
                </tr>
              </thead>

              <tbody>
                {modelEntries.map(([key, model]) => {
                  const isSelected =
                    String(key).toLowerCase() === String(selectedModel || '').toLowerCase()

                  return (
                    <tr
                      key={key}
                      className={[
                        'border-b border-[var(--bq-border)] last:border-b-0',
                        isSelected ? 'bg-violet-400/10' : 'hover:bg-[var(--bq-surface-alt)]',
                      ].join(' ')}
                    >
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-[var(--bq-text)]">
                            {modelDisplayName(key, model)}
                          </span>

                          {isSelected && (
                            <span className="rounded-full border border-violet-400/30 bg-violet-400/15 px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-violet-300">
                              Selected
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell value={model?.accuracy} percentage />
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell value={model?.roc_auc ?? model?.auc} percentage />
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell value={model?.balanced_accuracy} percentage />
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell value={model?.sensitivity} percentage />
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell value={model?.specificity} percentage />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex items-center gap-3 px-5 py-8 text-sm text-[var(--bq-text-dim)]">
            <AlertCircle className="size-5 text-amber-400" aria-hidden />
            <span>No benchmark model metrics are available yet.</span>
          </div>
        )}
      </section>

      {/* Calibration */}
      <section className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-400/10">
            <Gauge className="size-5 text-violet-300" aria-hidden />
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-bold text-[var(--bq-text)]">Calibration</h3>

            <p className="mt-1 text-xs leading-relaxed text-[var(--bq-text-dim)]">
              {calibrationMetric} values are displayed from the backend result rather than
              generated by the frontend.
            </p>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
                  Quantum / VQC
                </p>
                <p className="mt-2 font-mono text-lg font-bold text-[var(--bq-text)]">
                  {formatScore(quantumCalibration)}
                </p>
              </div>

              <div className="rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
                  Classical baseline
                </p>
                <p className="mt-2 font-mono text-lg font-bold text-[var(--bq-text)]">
                  {formatScore(classicalCalibration)}
                </p>
              </div>

              <div className="rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
                  Metric
                </p>
                <p className="mt-2 text-sm font-semibold text-[var(--bq-text)]">{calibrationMetric}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Decision checks */}
      <section className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-400/10">
            <ShieldCheck className="size-5 text-violet-300" aria-hidden />
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-bold text-[var(--bq-text)]">Decision checks</h3>

            <p className="mt-1 text-xs leading-relaxed text-[var(--bq-text-dim)]">
              These checks describe why the backend selected the displayed model path.
            </p>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <CheckCard
                label="Quantum robustness"
                passed={robustness}
                description="Checks whether the quantum model meets the configured robustness requirement."
              />

              <CheckCard
                label="Quantum improvement"
                passed={improves}
                description="Checks whether the quantum result improves the validated classical baseline under the configured comparison."
              />
            </div>
          </div>
        </div>
      </section>

      {/* Research note */}
      <div className="rounded-2xl border border-violet-400/30 bg-violet-400/10 px-5 py-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-violet-400">
          Research decision-support
        </p>

        <p className="mt-2 text-sm leading-relaxed text-[var(--bq-text)]">
          BIOQURE presents the benchmark and selection information produced by the backend.
          This panel does not independently choose a model or calculate a new winner from the
          displayed metrics.
        </p>
      </div>
    </div>
  )
}
