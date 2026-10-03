import {
  Atom,
  BarChart3,
  CircuitBoard,
  Cpu,
  Activity,
} from 'lucide-react'

function clamp01(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return 0
  return Math.min(1, Math.max(0, number))
}

function percent(value) {
  return `${(clamp01(value) * 100).toFixed(1)}%`
}

export default function ReportQuantum({ result = {}, quantum = null }) {
  const data = quantum || result?.quantum || {}

  const probabilities = data?.probabilities || {}

  const tumourProbability = clamp01(
    probabilities?.tumour ??
      probabilities?.tumor ??
      data?.tumour_probability ??
      data?.tumor_probability ??
      0,
  )

  const normalProbability = clamp01(
    probabilities?.normal ?? 1 - tumourProbability,
  )

  const scaledFeatures = Array.isArray(data?.scaled_features)
    ? data.scaled_features
    : []

  const measurements = data?.measurements || {}

  const angleMax = Number(data?.angle_bounds?.max) > 0 ? Number(data.angle_bounds.max) : 1

  const measurementEntries = Object.entries(measurements)

  const shots = Number(data?.shots)

  const totalMeasured = measurementEntries.reduce(
    (sum, [, count]) => sum + Number(count || 0),
    0,
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-cyan-500/10 ring-1 ring-cyan-400/15">
            <Atom
              className="size-5 text-[var(--gz-cyan-ui)]"
              aria-hidden
            />
          </div>

          <div>
            <p className="gz-label">Quantum model</p>

            <h2 className="mt-1 text-xl font-bold tracking-tight gz-heading">
              Variational quantum classifier simulation
            </h2>

            <p className="mt-1 max-w-3xl text-sm leading-relaxed text-[var(--gz-muted)]">
              Quantum-model information returned by the BIOQURE backend,
              including scaled features, circuit configuration, probabilities,
              and simulator measurements.
            </p>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <InfoCard
          icon={<Cpu className="size-4 text-cyan-300" />}
          label="Model"
          value={data?.model || 'VQC'}
        />

        <InfoCard
          icon={<CircuitBoard className="size-4 text-cyan-300" />}
          label="Simulator"
          value={data?.simulator || 'Qiskit Aer'}
        />

        <InfoCard
          icon={<CircuitBoard className="size-4 text-cyan-300" />}
          label="Feature map"
          value={data?.feature_map || 'ZZFeatureMap'}
        />

        <InfoCard
          icon={<Activity className="size-4 text-cyan-300" />}
          label="Shots"
          value={shots > 0 ? shots.toLocaleString() : '—'}
        />
      </section>

      {/* Probabilities */}
      <section className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-center gap-2">
          <BarChart3 className="size-4 text-cyan-300" aria-hidden />
          <h3 className="text-sm font-bold gz-heading">
            Class probabilities
          </h3>
        </div>

        <div className="mt-5 space-y-5">
          <ProbabilityRow
            label="Tumour"
            value={tumourProbability}
          />

          <ProbabilityRow
            label="Normal"
            value={normalProbability}
          />
        </div>
      </section>

      {/* Scaled features */}
      <section className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-center gap-2">
          <CircuitBoard className="size-4 text-cyan-300" aria-hidden />
          <h3 className="text-sm font-bold gz-heading">
            Scaled biomarker features
          </h3>
        </div>

        {scaledFeatures.length > 0 ? (
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {scaledFeatures.map((value, index) => {
              const numeric = Number(value)

              return (
                <div
                  key={index}
                  className="rounded-xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-4"
                >
                  <p className="gz-label">Feature {index + 1}</p>

                  <p className="mt-2 font-mono text-lg font-bold tabular-nums text-[var(--gz-cyan-ui)]">
                    {Number.isFinite(numeric)
                      ? numeric.toFixed(4)
                      : '—'}
                  </p>

                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[var(--gz-page)]">
                    <div
                      className="h-full rounded-full bg-cyan-300"
                      style={{
                        width: `${clamp01(numeric / angleMax) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="mt-4 text-sm text-[var(--gz-muted)]">
            No scaled feature vector was included in this result.
          </p>
        )}
      </section>

      {/* Measurements */}
      <section className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <BarChart3 className="size-4 text-cyan-300" aria-hidden />
              <h3 className="text-sm font-bold gz-heading">
                Simulator measurements
              </h3>
            </div>

            <p className="mt-1 text-xs text-[var(--gz-muted)]">
              Measurement counts returned by the quantum circuit simulator.
            </p>
          </div>

          <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1.5 font-mono text-[10px] text-cyan-200">
            {shots > 0 ? `${shots.toLocaleString()} shots` : 'Shots unavailable'}
          </span>
        </div>

        {measurementEntries.length > 0 ? (
          <div className="mt-5 space-y-3">
            {measurementEntries.map(([state, rawCount]) => {
              const count = Number(rawCount) || 0
              const denominator =
                shots > 0 ? shots : totalMeasured || 1

              const share = clamp01(count / denominator)

              return (
                <div key={state}>
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <span className="font-mono text-xs text-[var(--gz-heading)]">
                      {state}
                    </span>

                    <span className="font-mono text-xs tabular-nums text-[var(--gz-muted)]">
                      {count.toLocaleString()} · {percent(share)}
                    </span>
                  </div>

                  <div className="h-2.5 overflow-hidden rounded-full bg-[var(--gz-field-bg)] ring-1 ring-[var(--gz-border)]">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-teal-400 to-cyan-300"
                      style={{
                        width: `${share * 100}%`,
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="mt-5 text-sm text-[var(--gz-muted)]">
            No simulator measurement counts were included in this result.
          </p>
        )}
      </section>

      {/* Disclaimer */}
      <div className="rounded-2xl border border-cyan-400/15 bg-cyan-500/[0.05] px-5 py-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-200/80">
          Quantum simulation
        </p>

        <p className="mt-2 text-sm leading-relaxed text-[var(--gz-body)]">
          The quantum section represents a simulated quantum-machine-learning
          workflow. It is presented for research decision-support and does not
          constitute a clinical diagnosis.
        </p>
      </div>
    </div>
  )
}

function InfoCard({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-4">
      <div className="flex items-center gap-2 text-[var(--gz-muted)]">
        {icon}
        <span className="gz-label">{label}</span>
      </div>

      <p className="mt-3 break-words text-sm font-semibold text-[var(--gz-heading)]">
        {value}
      </p>
    </div>
  )
}

function ProbabilityRow({ label, value }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-[var(--gz-heading)]">
          {label}
        </span>

        <span className="font-mono text-sm font-bold text-[var(--gz-cyan-ui)]">
          {percent(value)}
        </span>
      </div>

      <div className="h-3 overflow-hidden rounded-full bg-[var(--gz-field-bg)] ring-1 ring-[var(--gz-border)]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-teal-400 to-cyan-300"
          style={{
            width: `${clamp01(value) * 100}%`,
          }}
        />
      </div>
    </div>
  )
}