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

function formatValue(value, digits = 4) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "Not reported";
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
      <div className="rounded-2xl border border-dashed border-[var(--bq-border-strong)] bg-[var(--bq-surface-alt)] px-6 py-10 text-center">
        <div className="text-sm font-bold text-[var(--bq-text)]">
          No biomarker signals returned
        </div>

        <p className="mt-1 text-xs leading-5 text-[var(--bq-text-dim)]">
          The current analysis response does not contain a biomarker
          summary.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)]">
      <div className="border-b border-[var(--bq-border)] bg-[var(--bq-surface-alt)] px-4 py-3">
        <div className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--bq-text-dim)]">
          Locked biomarker feature values
        </div>

        <div className="mt-1 text-xs text-[var(--bq-text-faint)]">
          Raw expression, transformed expression, and the exact values supplied
          to the classical and quantum endpoints. These are model inputs, not
          causal importance scores or clinical evidence.
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left">
          <thead>
            <tr className="border-b border-[var(--bq-border)] text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--bq-text-faint)]">
              <th className="px-4 py-3">Gene</th>
              <th className="px-4 py-3">Raw TPM</th>
              <th className="px-4 py-3">log2(TPM + 1)</th>
              <th className="px-4 py-3">Classical scaled</th>
              <th className="px-4 py-3">Quantum angle (rad)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--bq-border)]">
            {biomarkers.slice(0, limit).map((item, index) => {
              const gene = firstDefined(
                item?.gene,
                item?.gene_name,
                item?.feature,
                item?.name,
                `Feature ${index + 1}`
              );

              return (
                <tr key={`${gene}-${index}`}>
                  <td className="px-4 py-3 font-mono text-xs font-bold text-[var(--bq-text)]">
                    {gene}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-[var(--bq-text-dim)]">
                    {formatValue(firstDefined(item?.raw_tpm, item?.value, item?.expression))}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-[var(--bq-text-dim)]">
                    {formatValue(item?.log2_tpm_plus_1)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-[var(--bq-text-dim)]">
                    {formatValue(item?.classical_scaled_value)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-[var(--bq-text-dim)]">
                    {formatValue(item?.quantum_angle)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {biomarkers.length > limit && (
        <div className="border-t border-[var(--bq-border)] bg-[var(--bq-surface-alt)] px-4 py-3 text-center text-[11px] font-semibold text-[var(--bq-text-faint)]">
          Showing {limit} of {biomarkers.length} returned signals
        </div>
      )}
    </div>
  );
}
