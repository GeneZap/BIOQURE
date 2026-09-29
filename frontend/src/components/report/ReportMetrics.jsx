import {
  Activity,
  CheckCircle2,
  Gauge,
  ShieldCheck,
  Target,
} from 'lucide-react'

function clamp01(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return 0
  return Math.min(1, Math.max(0, number))
}

function percent(value, digits = 1) {
  return `${(clamp01(value) * 100).toFixed(digits)}%`
}

function modelName(key, model = {}) {
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

function probabilityFromModel(model) {
  if (!model) return null

  const value =
    model.tumour_probability ??
    model.tumor_probability ??
    model.probability ??
    model.predicted_probability

  const number = Number(value)

  return Number.isFinite(number) ? clamp01(number) : null
}

export default function ReportMetrics({ result = {}, metrics = null }) {
  const prediction = result?.prediction || {}

  const classicalModels =
    result?.classical_models ||
    result?.models ||
    metrics?.classical_models ||
    {}

  const selectedModel =
    prediction.selected_model ??
    result?.selected_model ??
    metrics?.selected_model ??
    'Not available'

  const label =
    prediction.label ??
    result?.label ??
    'Not available'

  const tumourProbability =
    prediction.tumour_probability ??
    prediction.tumor_probability ??
    result?.tumour_probability ??
    result?.tumor_probability

  const confidence =
    prediction.confidence ??
    metrics?.confidence ??
    result?.confidence

  const entries = Object.entries(classicalModels)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-cyan-500/10 ring-1 ring-cyan-400/15">
            <Activity
              className="size-5 text-[var(--gz-cyan-ui)]"
              aria-hidden
            />
          </div>

          <div>
            <p className="gz-label">Model metrics</p>

            <h2 className="mt-1 text-xl font-bold tracking-tight gz-heading">
              Classical machine-learning results
            </h2>

            <p className="mt-1 max-w-3xl text-sm leading-relaxed text-[var(--gz-muted)]">
              Model outputs and performance metrics supplied by the BIOQURE
              backend for the current research sample.
            </p>
          </div>
        </div>
      </div>

      {/* Prediction summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
          <div className="flex items-center gap-2">
            <Target className="size-4 text-cyan-300" aria-hidden />
            <span className="gz-label">Prediction</span>
          </div>

          <p className="mt-3 text-2xl font-bold text-[var(--gz-heading)]">
            {label}
          </p>
        </div>

        <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
          <div className="flex items-center gap-2">
            <Gauge className="size-4 text-cyan-300" aria-hidden />
            <span className="gz-label">Tumour probability</span>
          </div>

          <p className="mt-3 font-mono text-2xl font-bold text-[var(--gz-cyan-ui)]">
            {tumourProbability != null
              ? percent(tumourProbability)
              : '—'}
          </p>
        </div>

        <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-cyan-300" aria-hidden />
            <span className="gz-label">Selected model</span>
          </div>

          <p className="mt-3 text-lg font-bold text-[var(--gz-heading)]">
            {selectedModel}
          </p>

          {confidence != null && (
            <p className="mt-1 text-xs text-[var(--gz-muted)]">
              Display confidence:{' '}
              <span className="font-mono text-[var(--gz-body)]">
                {percent(confidence)}
              </span>
            </p>
          )}
        </div>
      </div>

      {/* Model cards */}
      {entries.length > 0 ? (
        <section className="space-y-3">
          {entries.map(([key, model]) => {
            const probability = probabilityFromModel(model)

            return (
              <article
                key={key}
                className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-[var(--gz-heading)]">
                      {modelName(key, model)}
                    </h3>

                    {probability != null && (
                      <p className="mt-1 text-xs text-[var(--gz-muted)]">
                        Tumour probability:{' '}
                        <span className="font-mono text-[var(--gz-cyan-ui)]">
                          {percent(probability)}
                        </span>
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {String(key).toLowerCase() ===
                      String(selectedModel).toLowerCase() && (
                      <span className="rounded-full bg-cyan-500/10 px-3 py-1 text-[9px] font-bold uppercase tracking-wider text-cyan-200">
                        Selected
                      </span>
                    )}

                    <CheckCircle2
                      className="size-5 text-emerald-300"
                      aria-hidden
                    />
                  </div>
                </div>

                {probability != null && (
                  <div className="mt-4">
                    <div className="h-2.5 overflow-hidden rounded-full bg-[var(--gz-field-bg)] ring-1 ring-[var(--gz-border)]">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-teal-400 to-cyan-300"
                        style={{
                          width: `${probability * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                )}

                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Metric
                    label="Accuracy"
                    value={model?.accuracy}
                  />

                  <Metric
                    label="AUC"
                    value={model?.auc}
                  />

                  <Metric
                    label="F1"
                    value={model?.f1}
                  />

                  <Metric
                    label="Brier"
                    value={model?.brier_score}
                  />
                </div>
              </article>
            )
          })}
        </section>
      ) : (
        <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-6 text-sm text-[var(--gz-muted)]">
          No classical model metrics are available in the current result.
        </div>
      )}
    </div>
  )
}

function Metric({ label, value }) {
  const number = Number(value)

  return (
    <div className="rounded-xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] px-3 py-3">
      <p className="text-[9px] font-bold uppercase tracking-wider text-[var(--gz-muted)]">
        {label}
      </p>

      <p className="mt-1 font-mono text-sm font-semibold tabular-nums text-[var(--gz-heading)]">
        {Number.isFinite(number)
          ? `${(number * 100).toFixed(1)}%`
          : '—'}
      </p>
    </div>
  )
}