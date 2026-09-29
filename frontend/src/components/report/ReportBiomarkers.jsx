import { Dna, Info, BarChart3 } from 'lucide-react'

function clamp01(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return 0
  return Math.min(1, Math.max(0, number))
}

export default function ReportBiomarkers({ biomarkers = [], result = null }) {
  const items = Array.isArray(biomarkers)
    ? biomarkers
    : Array.isArray(result?.biomarkers)
      ? result.biomarkers
      : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-cyan-500/10 ring-1 ring-cyan-400/15">
            <Dna
              className="size-5 text-[var(--gz-cyan-ui)]"
              aria-hidden
            />
          </div>

          <div className="min-w-0">
            <p className="gz-label">Biomarker report</p>

            <h2 className="mt-1 text-xl font-bold tracking-tight gz-heading">
              Training-selected biomarkers
            </h2>

            <p className="mt-1 max-w-3xl text-sm leading-relaxed text-[var(--gz-muted)]">
              The report shows the biomarkers used by the BIOQURE model,
              together with the sample value, relative importance, and the
              explanatory note supplied by the result.
            </p>
          </div>
        </div>
      </div>

      {/* Empty state */}
      {items.length === 0 ? (
        <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-6">
          <div className="flex items-start gap-3">
            <Info
              className="mt-0.5 size-5 shrink-0 text-amber-300"
              aria-hidden
            />

            <div>
              <p className="text-sm font-semibold text-[var(--gz-heading)]">
                No biomarker data available
              </p>

              <p className="mt-1 text-sm leading-relaxed text-[var(--gz-muted)]">
                The current result does not contain a biomarker list.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
              <div className="flex items-center gap-2 text-[var(--gz-muted)]">
                <Dna className="size-4 text-cyan-300" aria-hidden />
                <span className="gz-label">Biomarkers used</span>
              </div>

              <p className="mt-3 font-mono text-2xl font-bold text-[var(--gz-heading)]">
                {items.length}
              </p>

              <p className="mt-1 text-xs text-[var(--gz-muted)]">
                Features passed to the model for this sample.
              </p>
            </div>

            <div className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] p-5">
              <div className="flex items-center gap-2 text-[var(--gz-muted)]">
                <BarChart3
                  className="size-4 text-cyan-300"
                  aria-hidden
                />
                <span className="gz-label">Importance display</span>
              </div>

              <p className="mt-3 text-sm font-semibold text-[var(--gz-heading)]">
                Relative feature importance
              </p>

              <p className="mt-1 text-xs leading-relaxed text-[var(--gz-muted)]">
                Importance values are rendered from the backend result and are
                not recalculated by the frontend.
              </p>
            </div>
          </div>

          {/* Biomarker cards */}
          <div className="grid gap-4 md:grid-cols-2">
            {items.map((biomarker, index) => {
              const gene = biomarker?.gene || `Biomarker ${index + 1}`
              const value = biomarker?.value
              const importance = clamp01(biomarker?.importance)

              return (
                <article
                  key={`${gene}-${index}`}
                  className="rounded-2xl border border-[var(--gz-border)] bg-[var(--gz-surface)] p-5 transition-all duration-300 hover:border-cyan-400/20 hover:bg-[var(--gz-surface-hover)]"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="gz-label">Gene</p>

                      <h3 className="mt-1 font-mono text-xl font-bold tracking-tight text-[var(--gz-cyan-ui)]">
                        {gene}
                      </h3>
                    </div>

                    <div className="rounded-xl border border-cyan-400/20 bg-cyan-500/10 px-3 py-2 text-right">
                      <p className="text-[9px] font-bold uppercase tracking-wider text-cyan-200/70">
                        Sample value
                      </p>

                      <p className="mt-0.5 font-mono text-sm font-bold tabular-nums text-[var(--gz-cyan-ui)]">
                        {value != null && Number.isFinite(Number(value))
                          ? Number(value).toFixed(3)
                          : '—'}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <span className="gz-label">
                        Relative importance
                      </span>

                      <span className="font-mono text-xs font-semibold tabular-nums text-[var(--gz-cyan-ui)]">
                        {(importance * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="h-2.5 overflow-hidden rounded-full bg-[var(--gz-field-bg)] ring-1 ring-[var(--gz-border)]">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-teal-400 to-cyan-300 transition-all duration-700"
                        style={{
                          width: `${importance * 100}%`,
                        }}
                      />
                    </div>
                  </div>

                  <div className="mt-5 rounded-xl border border-[var(--gz-border)] bg-[var(--gz-field-bg)] px-4 py-3">
                    <div className="flex items-start gap-2.5">
                      <Info
                        className="mt-0.5 size-4 shrink-0 text-cyan-300"
                        aria-hidden
                      />

                      <p className="text-xs leading-relaxed text-[var(--gz-muted)]">
                        {biomarker?.note ||
                          'No explanatory note was supplied for this biomarker.'}
                      </p>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>

          {/* Method note */}
          <div className="rounded-2xl border border-cyan-400/15 bg-cyan-500/[0.05] px-5 py-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-200/80">
              Method note
            </p>

            <p className="mt-2 text-sm leading-relaxed text-[var(--gz-body)]">
              Biomarker selection belongs to the training pipeline. The
              frontend only displays the feature information contained in the
              BIOQURE result.
            </p>
          </div>
        </>
      )}
    </div>
  )
}