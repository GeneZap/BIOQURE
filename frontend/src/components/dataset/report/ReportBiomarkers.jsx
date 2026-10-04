import React, { useMemo } from "react";

function firstDefined(...values) {
  return values.find(
    (value) => value !== undefined && value !== null && value !== ""
  );
}

function normalizeBiomarkers(analysis) {
  const source =
    analysis?.biomarkers ??
    analysis?.biomarker_summary ??
    analysis?.result?.biomarkers ??
    [];

  if (Array.isArray(source)) {
    return source;
  }

  return Object.entries(source || {}).map(([gene, value]) => ({
    gene,
    value,
  }));
}

export default function ReportBiomarkers({
  analysis,
  limit = 8,
}) {
  const biomarkers = useMemo(
    () => normalizeBiomarkers(analysis),
    [analysis]
  );

  if (!biomarkers.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
        <div className="text-sm font-bold text-slate-800">
          No biomarker signals returned
        </div>

        <p className="mt-1 text-xs leading-5 text-slate-500">
          The current analysis response does not contain a biomarker
          summary.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
        <div className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">
          Biomarker signals
        </div>

        <div className="mt-1 text-xs text-slate-400">
          Feature-level values returned by the BIOQURE analysis service.
        </div>
      </div>

      <div className="grid grid-cols-[1fr_auto] gap-4 border-b border-slate-200 px-4 py-3 text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400">
        <span>Gene / feature</span>
        <span>Signal</span>
      </div>

      <div className="divide-y divide-slate-200">
        {biomarkers.slice(0, limit).map((item, index) => {
          const gene = firstDefined(
            item?.gene,
            item?.gene_name,
            item?.feature,
            item?.name,
            `Feature ${index + 1}`
          );

          const value = firstDefined(
            item?.value,
            item?.expression,
            item?.score,
            item?.importance,
            item?.signal
          );

          const direction = firstDefined(
            item?.direction,
            item?.trend
          );

          return (
            <div
              key={`${gene}-${index}`}
              className="grid grid-cols-[1fr_auto] items-center gap-4 px-4 py-3"
            >
              <div className="min-w-0">
                <div className="font-mono text-xs font-bold text-slate-800">
                  {gene}
                </div>

                {direction && (
                  <div className="mt-0.5 text-[10px] text-slate-400">
                    {direction}
                  </div>
                )}
              </div>

              <div className="text-right">
                <div className="font-mono text-xs font-semibold text-slate-600">
                  {typeof value === "number"
                    ? value.toFixed(4)
                    : String(value ?? "—")}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {biomarkers.length > limit && (
        <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 text-center text-[11px] font-semibold text-slate-400">
          Showing {limit} of {biomarkers.length} returned signals
        </div>
      )}
    </div>
  );
}