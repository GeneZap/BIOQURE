import React from "react";

function firstDefined(...values) {
  return values.find(
    (value) => value !== undefined && value !== null && value !== ""
  );
}

function StatusBadge({ active }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
        active
          ? "border-violet-200 bg-violet-50 text-violet-700"
          : "border-slate-200 bg-slate-50 text-slate-500"
      }`}
    >
      {active ? "Active" : "Not used"}
    </span>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0">
      <span className="text-xs font-medium text-slate-500">
        {label}
      </span>

      <span className="max-w-[65%] break-words text-right text-xs font-bold text-slate-800">
        {value ?? "—"}
      </span>
    </div>
  );
}

export default function ReportQuantum({
  analysis,
}) {
  const quantum =
    analysis?.quantum ??
    analysis?.quantum_metadata ??
    analysis?.runtime?.quantum ??
    {};

  const used = firstDefined(
    quantum?.used,
    analysis?.quantum_used,
    analysis?.runtime?.quantum_used
  );

  const fallbackUsed = firstDefined(
    analysis?.fallback_used,
    analysis?.runtime?.fallback_used
  );

  const backend = firstDefined(
    quantum?.backend,
    quantum?.backend_name,
    quantum?.execution_backend,
    analysis?.runtime?.backend,
    analysis?.runtime?.backend_name
  );

  const simulator = firstDefined(
    quantum?.simulator,
    quantum?.device,
    quantum?.execution_mode
  );

  const shots = firstDefined(
    quantum?.shots,
    quantum?.num_shots,
    analysis?.runtime?.shots
  );

  const featureMap = firstDefined(
    quantum?.feature_map,
    quantum?.featureMap,
    quantum?.encoding,
    "ZZFeatureMap"
  );

  const ansatz = firstDefined(
    quantum?.ansatz,
    quantum?.variational_form,
    quantum?.variational_circuit,
    "RealAmplitudes"
  );

  const optimizer = firstDefined(
    quantum?.optimizer,
    quantum?.optimization_method,
    quantum?.training_optimizer
  );

  const qubits = firstDefined(
    quantum?.qubits,
    quantum?.num_qubits,
    quantum?.n_qubits
  );

  const depth = firstDefined(
    quantum?.depth,
    quantum?.circuit_depth
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-black text-slate-900">
              Quantum inference
            </h3>

            <span className="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-[11px] font-semibold text-violet-700">
              Qiskit VQC
            </span>
          </div>

          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
            Quantum execution metadata returned by the BIOQURE inference
            service. Values are displayed from the backend response and are
            not inferred by the frontend.
          </p>
        </div>

        <StatusBadge active={used === true} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Quantum path
          </div>

          <div className="mt-2 text-lg font-extrabold text-slate-900">
            {used === true
              ? "Used"
              : used === false
                ? "Not used"
                : "—"}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Qubits
          </div>

          <div className="mt-2 text-lg font-extrabold text-slate-900">
            {qubits ?? "—"}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Shots
          </div>

          <div className="mt-2 text-lg font-extrabold text-slate-900">
            {shots ?? "—"}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Fallback
          </div>

          <div className="mt-2 text-lg font-extrabold text-slate-900">
            {fallbackUsed === true
              ? "Used"
              : fallbackUsed === false
                ? "Not used"
                : "—"}
          </div>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Architecture */}
        <div className="rounded-2xl border border-violet-200 bg-violet-50 p-5">
          <div className="text-xs font-bold uppercase tracking-[0.12em] text-violet-500">
            Circuit architecture
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-violet-200 bg-white">
            <div className="px-4">
              <InfoRow
                label="Feature map"
                value={featureMap}
              />

              <InfoRow
                label="Variational ansatz"
                value={ansatz}
              />

              <InfoRow
                label="Optimizer"
                value={optimizer}
              />

              <InfoRow
                label="Circuit depth"
                value={depth}
              />

              <InfoRow
                label="Qubits"
                value={qubits}
              />
            </div>
          </div>
        </div>

        {/* Runtime */}
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
            Quantum runtime
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="px-4">
              <InfoRow
                label="Backend"
                value={backend}
              />

              <InfoRow
                label="Execution mode"
                value={simulator}
              />

              <InfoRow
                label="Shots"
                value={shots}
              />

              <InfoRow
                label="Quantum execution"
                value={
                  used === true
                    ? "Enabled"
                    : used === false
                      ? "Disabled"
                      : "Not reported"
                }
              />

              <InfoRow
                label="Classical fallback"
                value={
                  fallbackUsed === true
                    ? "Enabled"
                    : fallbackUsed === false
                      ? "Not used"
                      : "Not reported"
                }
              />
            </div>
          </div>
        </div>
      </div>

      {/* Raw quantum metadata */}
      <details className="rounded-2xl border border-slate-200 bg-white">
        <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-600">
          View complete quantum metadata
        </summary>

        <div className="border-t border-slate-200 p-4">
          <pre className="max-h-[420px] overflow-auto rounded-xl bg-slate-950 p-4 text-[10px] leading-5 text-slate-200">
            {JSON.stringify(
              quantum,
              null,
              2
            )}
          </pre>
        </div>
      </details>
    </div>
  );
}