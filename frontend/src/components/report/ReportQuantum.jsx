import React from "react";

function firstDefined(...values) {
  return values.find(
    (value) => value !== undefined && value !== null && value !== ""
  );
}

function formatPercent(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(digits)}%` : "Not reported";
}

function formatSeedProbabilities(values) {
  if (!Array.isArray(values) || values.length === 0) return "Not reported";
  return values.map((value) => formatPercent(value, 1)).join(" · ");
}

function StatusBadge({ active }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
        active
          ? "border-violet-400/30 bg-violet-400/10 text-violet-300"
          : "border-[var(--bq-border)] bg-[var(--bq-surface-alt)] text-[var(--bq-text-dim)]"
      }`}
    >
      {active ? "Active" : "Not used"}
    </span>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[var(--bq-border)] py-3 last:border-b-0">
      <span className="text-xs font-medium text-[var(--bq-text-dim)]">
        {label}
      </span>
      <span className="max-w-[65%] break-words text-right text-xs font-bold text-[var(--bq-text)]">
        {value ?? "Not reported"}
      </span>
    </div>
  );
}

export default function ReportQuantum({ analysis }) {
  const quantum =
    analysis?.quantum ??
    analysis?.quantum_metadata ??
    analysis?.runtime?.quantum ??
    {};

  const primary = quantum?.primary_configuration ?? {};
  const secondary = quantum?.secondary_configuration ?? {};
  const predictions = analysis?.predictions ?? {};
  const candidateA = predictions?.quantum_candidate_a_mean ?? {};
  const balancedAE = predictions?.quantum_ae_balanced ?? {};
  const used = firstDefined(
    quantum?.used,
    analysis?.quantum_used,
    analysis?.runtime?.quantum_used
  );
  const fallbackUsed = firstDefined(
    quantum?.fallback_used,
    analysis?.fallback_used,
    analysis?.runtime?.fallback_used
  );
  const backend = firstDefined(
    quantum?.backend,
    quantum?.backend_name,
    quantum?.execution_backend,
    analysis?.runtime?.backend
  );
  const executionMode = firstDefined(
    quantum?.execution_mode,
    quantum?.simulator,
    quantum?.device
  );
  const shots = firstDefined(
    quantum?.shots,
    quantum?.num_shots,
    analysis?.runtime?.shots
  );
  const qubits = firstDefined(
    quantum?.qubits,
    quantum?.num_qubits,
    quantum?.n_qubits
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-black text-[var(--bq-text)]">
              Quantum inference
            </h3>
            <span className="inline-flex items-center rounded-full border border-violet-400/30 bg-violet-400/10 px-2.5 py-1 text-[11px] font-semibold text-violet-300">
              Qiskit VQC
            </span>
          </div>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--bq-text-dim)]">
            Configuration and runtime values reported by the locked backend.
            Candidate A and Candidate E have different circuit repetitions, so
            they are reported separately instead of inventing one circuit depth.
          </p>
        </div>
        <StatusBadge active={used === true} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Quantum path", used === true ? "Used" : used === false ? "Not used" : "Not reported"],
          ["Qubits", qubits ?? "Not reported"],
          ["Configured shots", shots ?? "Not reported"],
          ["Fallback", fallbackUsed === true ? "Used" : fallbackUsed === false ? "Not used" : "Not reported"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
              {label}
            </div>
            <div className="mt-2 text-lg font-extrabold text-[var(--bq-text)]">
              {value}
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-violet-400/30 bg-violet-400/10 p-5">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-violet-300">
            Candidate A five-seed mean
          </div>
          <div className="mt-3 text-3xl font-extrabold text-[var(--bq-text)]">
            {formatPercent(candidateA?.tumor_probability)}
          </div>
          <div className="mt-1 text-xs text-[var(--bq-text-dim)]">
            Tumor probability · threshold {candidateA?.threshold ?? "Not reported"}
          </div>
          <div className="mt-4 text-[11px] leading-5 text-[var(--bq-text-dim)]">
            Five separately seeded Candidate A VQCs are evaluated and their
            positive-class probabilities are averaged.
          </div>
          <InfoRow label="Seed probabilities" value={formatSeedProbabilities(candidateA?.seed_probabilities)} />
          <InfoRow label="Seed standard deviation" value={candidateA?.seed_standard_deviation?.toFixed?.(4)} />
        </div>

        <div className="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-5">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-emerald-300">
            A/E balanced ensemble
          </div>
          <div className="mt-3 text-3xl font-extrabold text-[var(--bq-text)]">
            {formatPercent(balancedAE?.tumor_probability)}
          </div>
          <div className="mt-1 text-xs text-[var(--bq-text-dim)]">
            Tumor probability · threshold {balancedAE?.threshold ?? "Not reported"}
          </div>
          <div className="mt-4 text-[11px] leading-5 text-[var(--bq-text-dim)]">
            This is not Candidate E alone. It combines the median probability
            from five Candidate A models with the median probability from five
            Candidate E models using the locked validation-selected weights.
          </div>
          <InfoRow label="Candidate A median" value={formatPercent(balancedAE?.candidate_a_median_probability)} />
          <InfoRow label="Candidate E median" value={formatPercent(balancedAE?.candidate_e_median_probability)} />
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-violet-400/30 bg-violet-400/10 p-5">
          <div className="text-xs font-bold uppercase tracking-[0.12em] text-violet-400">
            Candidate A architecture
          </div>
          <div className="mt-4 overflow-hidden rounded-xl border border-violet-400/30 bg-[var(--bq-surface)] px-4">
            <InfoRow label="Feature map" value={primary?.feature_map} />
            <InfoRow label="Feature-map repetitions" value={primary?.feature_map_reps} />
            <InfoRow label="Variational ansatz" value={primary?.ansatz} />
            <InfoRow label="Ansatz repetitions" value={primary?.ansatz_reps} />
            <InfoRow label="Entanglement" value={primary?.entanglement} />
            <InfoRow label="Optimizer" value={quantum?.optimizer} />
            <InfoRow label="Maximum iterations" value={quantum?.maxiter} />
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-5">
          <div className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
            Quantum runtime
          </div>
          <div className="mt-4 overflow-hidden rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface)] px-4">
            <InfoRow label="Backend" value={backend} />
            <InfoRow label="Execution mode" value={executionMode} />
            <InfoRow label="Configured shots" value={shots} />
            <InfoRow label="Qubits" value={qubits} />
            <InfoRow
              label="Quantum execution"
              value={used === true ? "Enabled" : used === false ? "Disabled" : "Not reported"}
            />
            <InfoRow
              label="Classical fallback"
              value={fallbackUsed === true ? "Enabled" : fallbackUsed === false ? "Not used" : "Not reported"}
            />
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] p-5">
        <div className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
          Balanced A/E ensemble
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <InfoRow label="Candidate A configuration" value={secondary?.candidate_a} />
          <InfoRow label="Candidate E configuration" value={secondary?.candidate_e} />
          <InfoRow label="Candidate A weight" value={secondary?.weight_candidate_a} />
          <InfoRow label="Candidate E weight" value={secondary?.weight_candidate_e} />
          <InfoRow label="Aggregation" value={secondary?.aggregation} />
          <InfoRow label="Decision threshold" value={secondary?.decision_threshold} />
          <InfoRow label="Candidate A seed probabilities" value={formatSeedProbabilities(balancedAE?.candidate_a_seed_probabilities)} />
          <InfoRow label="Candidate E seed probabilities" value={formatSeedProbabilities(balancedAE?.candidate_e_seed_probabilities)} />
        </div>
      </div>

      <details className="rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)]">
        <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-[var(--bq-text-dim)]">
          View complete quantum metadata
        </summary>
        <div className="border-t border-[var(--bq-border)] p-4">
          <pre className="max-h-[420px] overflow-auto rounded-xl bg-[#05080c] p-4 text-[10px] leading-5 text-[var(--bq-text-dim)]">
            {JSON.stringify(quantum, null, 2)}
          </pre>
        </div>
      </details>
    </div>
  );
}
