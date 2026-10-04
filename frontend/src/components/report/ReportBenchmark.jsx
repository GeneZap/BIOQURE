import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Gauge,
  ShieldCheck,
  XCircle,
} from "lucide-react";

function formatPercent(value, digits = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "Not recorded";
  return `${(Math.min(1, Math.max(0, number)) * 100).toFixed(digits)}%`;
}

function formatScore(value, digits = 3) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "Not recorded";
}

function modelDisplayName(key, model = {}) {
  if (model?.name) return model.name;
  const names = {
    classical_logistic: "Classical logistic regression",
    quantum_candidate_a_mean: "Candidate A quantum ensemble",
    quantum_ae_balanced: "A/E balanced quantum ensemble",
  };
  return names[key] || key;
}

function CheckCard({ label, passed, description }) {
  const known = typeof passed === "boolean";
  const positive = passed === true;
  return (
    <div
      className={[
        "rounded-2xl border p-4",
        !known
          ? "border-[var(--bq-border)] bg-[var(--bq-surface-alt)]"
          : positive
            ? "border-emerald-400/30 bg-emerald-400/10"
            : "border-amber-400/30 bg-amber-400/10",
      ].join(" ")}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-white/5">
          {positive ? (
            <CheckCircle2 className="size-5 text-emerald-300" aria-hidden />
          ) : known ? (
            <XCircle className="size-5 text-amber-300" aria-hidden />
          ) : (
            <AlertCircle className="size-5 text-[var(--bq-text-dim)]" aria-hidden />
          )}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--bq-text)]">{label}</p>
          <p className="mt-1 text-xs font-bold uppercase tracking-wider text-[var(--bq-text-dim)]">
            {!known ? "Not recorded" : positive ? "Passed" : "Not demonstrated"}
          </p>
          {description && (
            <p className="mt-2 text-xs leading-relaxed text-[var(--bq-text-dim)]">
              {description}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReportBenchmark({ analysis = null }) {
  const result = analysis || {};
  const benchmark = result?.benchmark ?? {};
  const checks = benchmark?.checks ?? {};
  const predictions = result?.predictions ?? {};
  const validationModels = benchmark?.models ?? {};
  const calibration = benchmark?.calibration ?? {};
  const deployment = result?.deployment_prediction ?? {};
  const selectedModel = deployment?.model ?? benchmark?.selected_model ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl border border-violet-400/30 bg-violet-400/10">
            <Gauge className="size-5 text-violet-300" aria-hidden />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--bq-text-faint)]">
              Locked endpoint comparison
            </p>
            <h2 className="mt-1 text-xl font-bold text-[var(--bq-text)]">
              Per-sample predictions and validation context
            </h2>
            <p className="mt-1 max-w-3xl text-sm text-[var(--bq-text-dim)]">
              The prediction table describes this sample. Validation metrics below
              come from the immutable model lock and are not recalculated here.
            </p>
          </div>
        </div>
        <div className="rounded-full border border-violet-400/30 bg-violet-400/10 px-4 py-2 text-center">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-violet-400">
            Deployment endpoint
          </p>
          <p className="mt-0.5 text-sm font-bold text-violet-300">
            {modelDisplayName(selectedModel)}
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-5">
          <div className="flex items-center gap-2 text-[var(--bq-text-dim)]">
            <ShieldCheck className="size-4 text-violet-400" aria-hidden />
            <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
              Selected model
            </span>
          </div>
          <p className="mt-3 text-lg font-bold text-[var(--bq-text)]">
            {benchmark?.selected_model_label || modelDisplayName(selectedModel)}
          </p>
          <p className="mt-1 text-xs text-[var(--bq-text-dim)]">
            Defined by the immutable deployment lock.
          </p>
        </div>
        <CheckCard
          label="Quantum robustness"
          passed={checks?.quantum_robust}
          description={checks?.quantum_robust_rule}
        />
        <CheckCard
          label="Quantum improvement"
          passed={checks?.quantum_improves}
          description={checks?.quantum_improvement_reason}
        />
      </div>

      <section className="overflow-hidden rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)]">
        <div className="border-b border-[var(--bq-border)] px-5 py-4">
          <h3 className="text-sm font-bold text-[var(--bq-text)]">
            Predictions for this sample
          </h3>
          <p className="mt-1 text-xs text-[var(--bq-text-dim)]">
            Quantum timing is shared because Candidate A and A/E are evaluated in one locked ensemble pass.
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
                        <span className="ml-2 rounded-full border border-violet-400/30 px-2 py-1 text-[9px] uppercase text-violet-300">
                          Deployment
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 font-mono text-xs text-[var(--bq-text)]">
                      {formatPercent(model?.tumor_probability)}
                    </td>
                    <td className="px-5 py-4 font-mono text-xs text-[var(--bq-text)]">
                      {formatScore(model?.threshold)}
                    </td>
                    <td className="px-5 py-4 text-xs font-semibold text-[var(--bq-text)]">
                      {model?.predicted_class ?? 'Not reported'}
                    </td>
                    <td className="px-5 py-4 text-xs text-[var(--bq-text-dim)]">
                      <span className="inline-flex items-center gap-1.5 font-mono">
                        <Clock3 className="size-3.5" aria-hidden />
                        {model?.inference_ms != null ? `${model.inference_ms} ms` : 'Not reported'}
                      </span>
                      {model?.timing_scope === 'shared_quantum_ensembles' && (
                        <span className="ml-2 text-[10px]">shared</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-5 py-8 text-sm text-[var(--bq-text-dim)]">
            No endpoint predictions were returned.
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-5">
        <h3 className="text-sm font-bold text-[var(--bq-text)]">
          Locked quantum validation metrics
        </h3>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left">
            <thead>
              <tr className="border-b border-[var(--bq-border)]">
                {['Endpoint', 'ROC-AUC', 'Balanced accuracy', 'Sensitivity', 'Specificity', 'MCC'].map((heading) => (
                  <th key={heading} className="px-3 py-3 text-[10px] font-bold uppercase text-[var(--bq-text-faint)]">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(validationModels).map(([key, model]) => (
                <tr key={key} className="border-b border-[var(--bq-border)] last:border-b-0">
                  <td className="px-3 py-3 text-xs font-semibold text-[var(--bq-text)]">{modelDisplayName(key, model)}</td>
                  <td className="px-3 py-3 font-mono text-xs">{formatScore(model?.roc_auc)}</td>
                  <td className="px-3 py-3 font-mono text-xs">{formatScore(model?.balanced_accuracy)}</td>
                  <td className="px-3 py-3 font-mono text-xs">{formatScore(model?.sensitivity)}</td>
                  <td className="px-3 py-3 font-mono text-xs">{formatScore(model?.specificity)}</td>
                  <td className="px-3 py-3 font-mono text-xs">{formatScore(model?.mcc)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-5">
        <h3 className="text-sm font-bold text-[var(--bq-text)]">Calibration</h3>
        <p className="mt-1 text-xs text-[var(--bq-text-dim)]">
          Only calibration values recorded in the immutable lock are displayed.
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-4">
            <p className="text-[10px] font-bold uppercase text-[var(--bq-text-faint)]">Candidate A</p>
            <p className="mt-2 font-mono text-lg font-bold">{formatScore(calibration?.quantum_candidate_a)}</p>
          </div>
          <div className="rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-4">
            <p className="text-[10px] font-bold uppercase text-[var(--bq-text-faint)]">A/E balanced</p>
            <p className="mt-2 font-mono text-lg font-bold">{formatScore(calibration?.quantum_ae_balanced)}</p>
          </div>
          <div className="rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-4">
            <p className="text-[10px] font-bold uppercase text-[var(--bq-text-faint)]">Metric</p>
            <p className="mt-2 text-sm font-semibold">{calibration?.metric || 'Not recorded'}</p>
          </div>
        </div>
        {calibration?.classical_note && (
          <p className="mt-3 text-xs text-[var(--bq-text-dim)]">{calibration.classical_note}</p>
        )}
      </section>
    </div>
  );
}
