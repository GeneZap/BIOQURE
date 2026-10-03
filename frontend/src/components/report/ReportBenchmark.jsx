import {
  AlertCircle,
  CheckCircle2,
  CircleDashed,
  Clock3,
  Gauge,
  ShieldCheck,
  XCircle,
} from 'lucide-react'

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function clamp01(value) {
  const number = toNumber(value)
  return number == null ? null : Math.min(1, Math.max(0, number))
}

function firstBoolean(...values) {
  const found = values.find((value) => typeof value === 'boolean')
  return found === undefined ? null : found
}

function formatPercent(value, digits = 1) {
  const number = clamp01(value)
  return number == null ? '—' : `${(number * 100).toFixed(digits)}%`
}

function formatScore(value, digits = 3) {
  const number = toNumber(value)
  return number == null ? '—' : number.toFixed(digits)
}

function modelDisplayName(key, model = {}) {
  if (model?.name) return model.name

  const names = {
    logistic_regression: 'Logistic Regression',
    rbf_svm: 'RBF-SVM',
    xgboost: 'XGBoost',
    mlp: 'MLP',
    vqc: 'VQC',
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
  if (passed == null) {
    return (
      <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-[var(--gz-surface)]">
            <CircleDashed className="size-5 text-[var(--gz-muted)]" aria-hidden />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[var(--gz-heading)]">{label}</p>
            <p className="mt-1 text-xs font-bold uppercase tracking-wider text-[var(--gz-muted)]">
              Not evaluated
            </p>
            <p className="mt-2 text-xs leading-relaxed text-[var(--gz-muted)]">
              The backend did not report this check for the current result.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={[
        'rounded-2xl border p-4 transition-all duration-300',
        passed
          ? 'border-emerald-400/25 bg-emerald-500/[0.08]'
          : 'border-rose-400/25 bg-rose-500/[0.07]',
      ].join(' ')}
    >
      <div className="flex items-start gap-3">
        <div
          className={[
            'mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl',
            passed ? 'bg-emerald-500/10' : 'bg-rose-500/10',
          ].join(' ')}
        >
          {passed ? (
            <CheckCircle2
              className="size-5 text-emerald-300"
              aria-hidden
            />
          ) : (
            <XCircle
              className="size-5 text-rose-300"
              aria-hidden
            />
          )}
        </div>

        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--gz-heading)]">
            {label}
          </p>

          <p
            className={[
              'mt-1 text-xs font-bold uppercase tracking-wider',
              passed ? 'text-emerald-300' : 'text-rose-300',
            ].join(' ')}
          >
            {passed ? 'Passed' : 'Not passed'}
          </p>

          {description && (
            <p className="mt-2 text-xs leading-relaxed text-[var(--gz-muted)]">
              {description}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function MetricCell({ value, percentage = false }) {
  return (
    <span className="font-mono text-xs tabular-nums text-[var(--gz-body)]">
      {percentage ? formatPercent(value) : formatScore(value)}
    </span>
  )
}

export default function ReportBenchmark({ benchmark = {}, result = null }) {
  const models = benchmark?.models || {}
  const checks = benchmark?.checks || {}
  const calibration = benchmark?.calibration || {}

  const modelEntries = Object.entries(models)

  const selectedModel =
    result?.prediction?.selected_model ??
    result?.selected_model ??
    benchmark?.selected_model ??
    null

  const bestClassical =
    benchmark?.best_classical_model ??
    result?.selection?.best_classical_model ??
    null

  const outcome = outcomeLabel(
    benchmark?.outcome ??
      result?.selection?.outcome ??
      result?.prediction?.selected_model
  )

  const robustness = firstBoolean(checks?.quantum_robust, checks?.robust)

  const improves = firstBoolean(checks?.quantum_improves, checks?.improves)

  const selectedKey =
    benchmark?.selected_model_key ??
    result?.prediction?.selected_model_key ??
    result?.selected_model_key ??
    null

  const calibrationMetric =
    calibration?.metric ||
    calibration?.name ||
    'Calibration'

  const quantumCalibration =
    calibration?.quantum ??
    calibration?.vqc ??
    calibration?.quantum_brier_score

  const classicalCalibration =
    calibration?.classical_baseline ??
    calibration?.classical ??
    calibration?.classical_brier_score

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-cyan-500/10 ring-1 ring-cyan-400/15">
            <Gauge
              className="size-5 text-[var(--gz-cyan-ui)]"
              aria-hidden
            />
          </div>

          <div className="min-w-0">
            <p className="gz-label">Benchmark & decision</p>
            <h2 className="mt-1 text-xl font-bold tracking-tight gz-heading">
              Classical vs quantum evaluation
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[var(--gz-muted)]">
              Validation metrics, calibration information, and the model
              selection checks used by the BIOQURE decision layer.
            </p>
          </div>
        </div>

        <div className="shrink-0 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-4 py-2 text-center">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-200/80">
            Outcome
          </p>
          <p className="mt-0.5 text-sm font-bold text-[var(--gz-cyan-ui)]">
            {outcome}
          </p>
        </div>
      </div>

      {/* Selection summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
          <div className="flex items-center gap-2 text-[var(--gz-muted)]">
            <ShieldCheck className="size-4 text-cyan-300" aria-hidden />
            <span className="gz-label">Selected model</span>
          </div>

          <p className="mt-3 text-lg font-bold gz-heading">
            {selectedModel || 'Not available'}
          </p>

          {bestClassical && (
            <p className="mt-1 text-xs text-[var(--gz-muted)]">
              Best classical baseline:{' '}
              <span className="font-semibold text-[var(--gz-body)]">
                {bestClassical}
              </span>
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
          <div className="flex items-center gap-2 text-[var(--gz-muted)]">
            <CheckCircle2
              className="size-4 text-emerald-300"
              aria-hidden
            />
            <span className="gz-label">Quantum robustness</span>
          </div>

          <p
            className={[
              'mt-3 text-lg font-bold',
              robustness == null
                ? 'text-[var(--gz-muted)]'
                : robustness
                  ? 'text-emerald-300'
                  : 'text-rose-300',
            ].join(' ')}
          >
            {robustness == null
              ? 'Not evaluated'
              : robustness
                ? 'Passed'
                : 'Not passed'}
          </p>

          <p className="mt-1 text-xs text-[var(--gz-muted)]">
            Based on the backend benchmark check.
          </p>
        </div>

        <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
          <div className="flex items-center gap-2 text-[var(--gz-muted)]">
            <Gauge className="size-4 text-cyan-300" aria-hidden />
            <span className="gz-label">Quantum improvement</span>
          </div>

          <p
            className={[
              'mt-3 text-lg font-bold',
              improves == null
                ? 'text-[var(--gz-muted)]'
                : improves
                  ? 'text-emerald-300'
                  : 'text-amber-300',
            ].join(' ')}
          >
            {improves == null
              ? 'Not evaluated'
              : improves
                ? 'Demonstrated'
                : 'Not demonstrated'}
          </p>

          <p className="mt-1 text-xs text-[var(--gz-muted)]">
            Compared with the validated classical baseline.
          </p>
        </div>
      </div>

      {/* Model comparison */}
      <section className="overflow-hidden rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)]">
        <div className="border-b border-[var(--gz-border)] px-5 py-4">
          <div className="flex items-center gap-2">
            <Gauge className="size-4 text-cyan-300" aria-hidden />
            <h3 className="text-sm font-bold gz-heading">
              Model comparison
            </h3>
          </div>

          <p className="mt-1 text-xs text-[var(--gz-muted)]">
            The same held-out benchmark should be used for every model shown
            here.
          </p>
        </div>

        {modelEntries.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left">
              <thead>
                <tr className="border-b border-[var(--gz-border)] bg-[var(--gz-field-bg)]/70">
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--gz-muted)]">
                    Model
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--gz-muted)]">
                    Accuracy
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--gz-muted)]">
                    AUC
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--gz-muted)]">
                    F1
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--gz-muted)]">
                    Brier score
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-[var(--gz-muted)]">
                    Inference
                  </th>
                </tr>
              </thead>

              <tbody>
                {modelEntries.map(([key, model]) => {
                  const isSelected =
                    key === selectedKey ||
                    String(key).toLowerCase() ===
                      String(selectedModel || '').toLowerCase()

                  return (
                    <tr
                      key={key}
                      className={[
                        'border-b border-[var(--gz-border)] last:border-b-0',
                        isSelected
                          ? 'bg-cyan-500/[0.06]'
                          : 'hover:bg-[var(--gz-field-bg)]/60',
                      ].join(' ')}
                    >
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-[var(--gz-heading)]">
                            {modelDisplayName(key, model)}
                          </span>

                          {isSelected && (
                            <span className="rounded-full bg-cyan-500/10 px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-cyan-200">
                              Selected
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell
                          value={model?.accuracy}
                          percentage
                        />
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell
                          value={model?.auc}
                          percentage
                        />
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell
                          value={model?.f1}
                          percentage
                        />
                      </td>

                      <td className="px-5 py-4">
                        <MetricCell value={model?.brier_score} />
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1.5 text-xs text-[var(--gz-muted)]">
                          <Clock3 className="size-3.5" aria-hidden />
                          <span className="font-mono">
                            {model?.inference_ms != null
                              ? `${model.inference_ms} ms`
                              : '—'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex items-center gap-3 px-5 py-8 text-sm text-[var(--gz-muted)]">
            <AlertCircle className="size-5 text-amber-300" aria-hidden />
            <span>
              No benchmark model metrics are available yet.
            </span>
          </div>
        )}
      </section>

      {/* Calibration */}
      <section className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-cyan-500/10">
            <Gauge
              className="size-5 text-cyan-300"
              aria-hidden
            />
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-bold gz-heading">
              Calibration
            </h3>

            <p className="mt-1 text-xs leading-relaxed text-[var(--gz-muted)]">
              {calibrationMetric} values are displayed from the backend result
              rather than generated by the frontend.
            </p>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-4">
                <p className="gz-label">Quantum / VQC</p>
                <p className="mt-2 font-mono text-lg font-bold text-[var(--gz-heading)]">
                  {formatScore(quantumCalibration)}
                </p>
              </div>

              <div className="rounded-xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-4">
                <p className="gz-label">Classical baseline</p>
                <p className="mt-2 font-mono text-lg font-bold text-[var(--gz-heading)]">
                  {formatScore(classicalCalibration)}
                </p>
              </div>

              <div className="rounded-xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-4">
                <p className="gz-label">Metric</p>
                <p className="mt-2 text-sm font-semibold text-[var(--gz-heading)]">
                  {calibrationMetric}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Decision checks */}
      <section className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-cyan-500/10">
            <ShieldCheck
              className="size-5 text-cyan-300"
              aria-hidden
            />
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-bold gz-heading">
              Decision checks
            </h3>

            <p className="mt-1 text-xs leading-relaxed text-[var(--gz-muted)]">
              These checks describe why the backend selected the displayed
              model path.
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
      <div className="rounded-2xl border border-cyan-400/15 bg-cyan-500/[0.05] px-5 py-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-200/80">
          Research decision-support
        </p>

        <p className="mt-2 text-sm leading-relaxed text-[var(--gz-body)]">
          BIOQURE presents the benchmark and selection information produced by
          the backend. This panel does not independently choose a model or
          calculate a new winner from the displayed metrics.
        </p>
      </div>
    </div>
  )
}