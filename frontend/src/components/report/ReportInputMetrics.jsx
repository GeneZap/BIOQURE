import {
  Database,
  Dna,
  FileText,
  Hash,
} from 'lucide-react'

export default function ReportInputMetrics({
  result = {},
  inputMetrics = null,
}) {
  const metrics =
    inputMetrics ||
    result?.input_metrics ||
    {}

  const biomarkerValues =
    metrics?.biomarker_values_used ||
    metrics?.biomarkers ||
    {}

  const entries = Object.entries(biomarkerValues)

  const samples = metrics?.samples
  const genesDetected =
    metrics?.genes_detected ??
    metrics?.genesDetected

  const biomarkersUsed =
    metrics?.biomarkers_used ??
    metrics?.biomarkersUsed

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-cyan-500/10 ring-1 ring-cyan-400/15">
            <Database
              className="size-5 text-[var(--gz-cyan-ui)]"
              aria-hidden
            />
          </div>

          <div>
            <p className="gz-label">Raw input metrics</p>

            <h2 className="mt-1 text-xl font-bold tracking-tight gz-heading">
              Expression input summary
            </h2>

            <p className="mt-1 max-w-3xl text-sm leading-relaxed text-[var(--gz-muted)]">
              Basic metrics describing the expression input and the biomarker
              values passed into the BIOQURE inference pipeline.
            </p>
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          icon={<FileText className="size-4 text-cyan-300" />}
          label="Samples"
          value={formatNumber(samples)}
        />

        <MetricCard
          icon={<Dna className="size-4 text-cyan-300" />}
          label="Genes detected"
          value={formatNumber(genesDetected)}
        />

        <MetricCard
          icon={<Hash className="size-4 text-cyan-300" />}
          label="Biomarkers used"
          value={formatNumber(biomarkersUsed)}
        />
      </div>

      {/* Biomarker values */}
      <section className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-center gap-2">
          <Dna className="size-4 text-cyan-300" aria-hidden />

          <h3 className="text-sm font-bold gz-heading">
            Biomarker values used
          </h3>
        </div>

        {entries.length > 0 ? (
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {entries.map(([gene, rawValue]) => {
              const value = Number(rawValue)

              return (
                <div
                  key={gene}
                  className="rounded-xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-4"
                >
                  <p className="font-mono text-sm font-bold text-[var(--gz-cyan-ui)]">
                    {gene}
                  </p>

                  <p className="mt-2 font-mono text-lg font-semibold tabular-nums text-[var(--gz-heading)]">
                    {Number.isFinite(value)
                      ? value.toFixed(4)
                      : String(rawValue)}
                  </p>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="mt-4 rounded-xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5 text-sm text-[var(--gz-muted)]">
            No biomarker values were included in the current result.
          </div>
        )}
      </section>

      {/* Processing note */}
      <div className="rounded-2xl border border-cyan-400/15 bg-cyan-500/[0.05] px-5 py-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-200/80">
          Input handling
        </p>

        <p className="mt-2 text-sm leading-relaxed text-[var(--gz-body)]">
          These values describe what was actually passed to the result
          pipeline. The frontend displays the backend output and does not
          independently preprocess the expression data.
        </p>
      </div>
    </div>
  )
}

function formatNumber(value) {
  const number = Number(value)

  if (!Number.isFinite(number)) return '—'

  return number.toLocaleString()
}

function MetricCard({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
      <div className="flex items-center gap-2 text-[var(--gz-muted)]">
        {icon}
        <span className="gz-label">{label}</span>
      </div>

      <p className="mt-3 font-mono text-2xl font-bold tabular-nums text-[var(--gz-heading)]">
        {value}
      </p>
    </div>
  )
}