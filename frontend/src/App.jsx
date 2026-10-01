import React, { useMemo, useState } from "react";
import DatasetPoolPanel from "./components/dataset/DatasetPoolPanel.jsx";
import ReportMetrics from "./components/report/ReportMetrics.jsx";
import ReportBenchmark from "./components/report/ReportBenchmark.jsx";
import ReportQuantum from "./components/report/ReportQuantum.jsx";
import ReportBiomarkers from "./components/report/ReportBiomarkers.jsx";
import ReportInputMetrics from "./components/report/ReportInputMetrics.jsx";

/* =========================================================
   HELPERS
   ========================================================= */

function firstDefined(...values) {
  return values.find(
    (value) => value !== undefined && value !== null && value !== ""
  );
}

function getPrediction(result) {
  const prediction = firstDefined(
    result?.prediction,
    result?.result?.prediction,
    result?.classification
  );

  if (typeof prediction === "string") {
    return prediction;
  }

  return firstDefined(
    prediction?.label,
    prediction?.class_label,
    prediction?.prediction,
    result?.predicted_label,
    result?.predicted_class,
    result?.label,
    "—"
  );
}

function getConfidence(result) {
  const prediction = firstDefined(
    result?.prediction,
    result?.result?.prediction
  );

  return firstDefined(
    prediction?.probability,
    prediction?.confidence,
    prediction?.score,
    result?.probability,
    result?.confidence,
    result?.score
  );
}

function getModel(result) {
  return firstDefined(
    result?.model_selection?.selected_model,
    result?.model_selection?.model,
    result?.selected_model,
    result?.model,
    result?.inference?.selected_model,
    "—"
  );
}

function getQuantumState(result) {
  const value = firstDefined(
    result?.quantum?.used,
    result?.quantum_used,
    result?.runtime?.quantum_used,
    result?.inference?.quantum_used
  );

  if (value === true) return "Used";
  if (value === false) return "Not used";

  return "—";
}

/* =========================================================
   UI COMPONENTS
   ========================================================= */

function Badge({ children, tone = "neutral" }) {
  const styles = {
    neutral: "border-slate-200 bg-slate-50 text-slate-600",
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    purple: "border-violet-200 bg-violet-50 text-violet-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
        styles[tone] || styles.neutral
      }`}
    >
      {children}
    </span>
  );
}

function TabButton({
  active,
  children,
  onClick,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl px-3 py-2 text-xs font-bold transition ${
        active
          ? "bg-slate-900 text-white shadow-sm"
          : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
      }`}
    >
      {children}
    </button>
  );
}

function WorkflowStep({
  number,
  label,
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-[10px] font-bold text-white">
        {number}
      </span>

      <span className="text-xs font-semibold text-slate-700">
        {label}
      </span>
    </div>
  );
}

function LockedInferenceSummary({ result }) {
  const predictions = result?.predictions || {};
  const labels = {
    classical_logistic: "Logistic regression",
    quantum_candidate_a_mean: "Candidate A quantum ensemble",
    quantum_ae_balanced: "A/E quantum ensemble",
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3">
        {Object.entries(predictions).map(([key, prediction]) => (
          <div key={key} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-bold text-slate-700">{labels[key] || key}</div>
            <div className="mt-2 text-xl font-black text-slate-950">{prediction.predicted_class}</div>
            <div className="mt-1 text-xs text-slate-500">Estimated tumor-class probability: {(prediction.tumor_probability * 100).toFixed(1)}%</div>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-2xl border border-slate-200">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-400"><tr><th className="px-3 py-2">Biomarker</th><th className="px-3 py-2">Raw TPM</th><th className="px-3 py-2">log2(TPM + 1)</th><th className="px-3 py-2">Quantum angle</th></tr></thead>
          <tbody>{(result?.biomarkers || []).map((row) => <tr key={row.gene_name} className="border-t border-slate-100"><td className="px-3 py-2 font-bold">{row.gene_name}</td><td className="px-3 py-2">{row.raw_tpm.toFixed(4)}</td><td className="px-3 py-2">{row.log2_tpm_plus_1.toFixed(4)}</td><td className="px-3 py-2">{row.quantum_angle.toFixed(4)}</td></tr>)}</tbody>
        </table>
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-slate-500"><span>Agreement: {result?.agreement?.summary}</span><span>Lock: {result?.model_lock?.lock_sha256?.slice(0, 12)}…</span><span>Total: {result?.timing_ms?.total} ms</span></div>
      <p className="text-xs font-semibold text-amber-700">Research demonstration only. This output is not a medical diagnosis and must not be used for clinical decisions.</p>
    </div>
  );
}

/* =========================================================
   APP
   ========================================================= */

export default function App() {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  const prediction = useMemo(
    () => getPrediction(analysis),
    [analysis]
  );

  const confidence = useMemo(
    () => getConfidence(analysis),
    [analysis]
  );

  const selectedModel = useMemo(
    () => getModel(analysis),
    [analysis]
  );

  const quantumState = useMemo(
    () => getQuantumState(analysis),
    [analysis]
  );

  function handleDatasetSelect(dataset) {
    setSelectedDataset(dataset);
    setAnalysis(null);
    setActiveTab("overview");
  }

  function handleAnalysisComplete(result, dataset) {
    setAnalysis(result);

    if (dataset) {
      setSelectedDataset(dataset);
    }

    setActiveTab("overview");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* =====================================================
          HEADER
          ===================================================== */}

      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-sm font-black text-white">
              BQ
            </div>

            <div className="min-w-0">
              <div className="truncate text-base font-black tracking-tight">
                BIOQURE
              </div>

              <div className="hidden text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400 sm:block">
                Breast Cancer Research Intelligence
              </div>
            </div>
          </div>

          <div className="hidden items-center gap-2 md:flex">
            <Badge tone="blue">RNA-seq</Badge>
            <Badge tone="purple">Classical ML</Badge>
            <Badge tone="purple">Quantum ML</Badge>
          </div>

          <Badge tone={analysis ? "green" : "neutral"}>
            {analysis ? "Analysis available" : "Research mode"}
          </Badge>
        </div>
      </header>

      {/* =====================================================
          MAIN
          ===================================================== */}

      <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
        {/* ===================================================
            HERO
            =================================================== */}

        <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="grid gap-6 px-5 py-7 lg:grid-cols-[1.35fr_0.65fr] lg:px-8 lg:py-9">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="blue">BIOQURE PLATFORM</Badge>
                <Badge tone="green">PUBLIC DATA</Badge>
              </div>

              <h1 className="mt-4 max-w-4xl text-3xl font-black tracking-tight text-slate-950 sm:text-4xl lg:text-5xl">
                Breast-cancer expression analysis with classical and quantum
                machine learning.
              </h1>

              <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-500 sm:text-base">
                Explore curated public expression datasets, apply the BIOQURE
                preprocessing pipeline, and inspect model inference,
                benchmark information, biomarker signals, and quantum runtime
                metadata from a single research workspace.
              </p>

              <div className="mt-6 flex flex-wrap gap-2">
                <span className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">
                  Curated TCGA/GDC datasets
                </span>

                <span className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">
                  Shared preprocessing
                </span>

                <span className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">
                  Classical baseline
                </span>

                <span className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">
                  Qiskit VQC
                </span>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">
                Workflow
              </div>

              <div className="mt-4 space-y-3">
                <WorkflowStep
                  number="01"
                  label="Select dataset"
                />

                <WorkflowStep
                  number="02"
                  label="Preprocess expression"
                />

                <WorkflowStep
                  number="03"
                  label="Run model inference"
                />

                <WorkflowStep
                  number="04"
                  label="Inspect research output"
                />
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================
            DATASET WORKSPACE
            =================================================== */}

        <section className="mt-6">
          <DatasetPoolPanel
            selectedDatasetId={selectedDataset?.id}
            onDatasetSelect={handleDatasetSelect}
            onAnalysisComplete={handleAnalysisComplete}
          />
        </section>

        {/* ===================================================
            REPORT
            =================================================== */}

        {analysis ? (
          <section className="mt-6">
            <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
              {/* Report header */}
              <div className="border-b border-slate-200 px-5 py-5 sm:px-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone="green">
                        INFERENCE COMPLETE
                      </Badge>

                      {selectedDataset?.id && (
                        <Badge>
                          {selectedDataset.id}
                        </Badge>
                      )}
                    </div>

                    <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-900">
                      BIOQURE Research Report
                    </h2>

                    <p className="mt-1 text-sm text-slate-500">
                      Model output and runtime information for the selected
                      public dataset.
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
                      Prediction
                    </div>

                    <div className="mt-1 text-sm font-extrabold text-slate-800">
                      {prediction}
                    </div>

                    <div className="mt-1 text-[10px] text-slate-400">
                      Model: {selectedModel}
                    </div>
                  </div>
                </div>

                {/* =================================================
                    REPORT TABS
                    ================================================= */}

                <div className="mt-5 flex flex-wrap gap-1 rounded-2xl bg-slate-100 p-1">
                  <TabButton
                    active={activeTab === "overview"}
                    onClick={() => setActiveTab("overview")}
                  >
                    Overview
                  </TabButton>

                  <TabButton
                    active={activeTab === "benchmark"}
                    onClick={() => setActiveTab("benchmark")}
                  >
                    Benchmark
                  </TabButton>

                  <TabButton
                    active={activeTab === "quantum"}
                    onClick={() => setActiveTab("quantum")}
                  >
                    Quantum
                  </TabButton>

                  <TabButton
                    active={activeTab === "biomarkers"}
                    onClick={() => setActiveTab("biomarkers")}
                  >
                    Biomarkers
                  </TabButton>

                  <TabButton
                    active={activeTab === "input"}
                    onClick={() => setActiveTab("input")}
                  >
                    Input metrics
                  </TabButton>
                </div>
              </div>

              {/* =================================================
                  REPORT CONTENT
                  ================================================= */}

              <div className="p-5 sm:p-6">
                {/* OVERVIEW */}
                {activeTab === "overview" && (
                  <div className="space-y-5">
                    <LockedInferenceSummary result={analysis} />
                    <ReportMetrics
                      analysis={analysis}
                      dataset={selectedDataset}
                    />

                    <div className="grid gap-5 lg:grid-cols-2">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                        <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
                          Model execution
                        </div>

                        <div className="mt-4 space-y-3">
                          <div className="flex items-center justify-between gap-4">
                            <span className="text-sm text-slate-500">
                              Selected model
                            </span>

                            <span className="text-sm font-bold text-slate-800">
                              {selectedModel}
                            </span>
                          </div>

                          <div className="flex items-center justify-between gap-4">
                            <span className="text-sm text-slate-500">
                              Prediction
                            </span>

                            <span className="text-sm font-bold text-slate-800">
                              {prediction}
                            </span>
                          </div>

                          <div className="flex items-center justify-between gap-4">
                            <span className="text-sm text-slate-500">
                              Confidence
                            </span>

                            <span className="text-sm font-bold text-slate-800">
                              {confidence !== undefined &&
                              confidence !== null
                                ? confidence
                                : "—"}
                            </span>
                          </div>

                          <div className="flex items-center justify-between gap-4">
                            <span className="text-sm text-slate-500">
                              Quantum path
                            </span>

                            <Badge
                              tone={
                                quantumState === "Used"
                                  ? "purple"
                                  : "neutral"
                              }
                            >
                              {quantumState}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                        <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
                          Dataset context
                        </div>

                        <div className="mt-4 space-y-3">
                          <div className="flex items-center justify-between gap-4">
                            <span className="text-sm text-slate-500">
                              Dataset ID
                            </span>

                            <span className="font-mono text-xs font-bold text-slate-800">
                              {selectedDataset?.id || "—"}
                            </span>
                          </div>

                          <div className="flex items-center justify-between gap-4">
                            <span className="text-sm text-slate-500">
                              Project
                            </span>

                            <span className="text-sm font-bold text-slate-800">
                              {selectedDataset?.project || "—"}
                            </span>
                          </div>

                          <div className="flex items-center justify-between gap-4">
                            <span className="text-sm text-slate-500">
                              Source
                            </span>

                            <span className="text-sm font-bold text-slate-800">
                              {selectedDataset?.source || "—"}
                            </span>
                          </div>

                          <div className="flex items-center justify-between gap-4">
                            <span className="text-sm text-slate-500">
                              Data type
                            </span>

                            <span className="text-sm font-bold text-slate-800">
                              {selectedDataset?.dataType || "—"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                      <div className="text-xs font-bold text-amber-800">
                        Research-use notice
                      </div>

                      <p className="mt-1 text-xs leading-5 text-amber-700">
                        BIOQURE presents computational research output for
                        exploration and benchmarking. Model predictions and
                        biomarker signals should not be interpreted as a
                        standalone clinical diagnosis or treatment decision.
                      </p>
                    </div>
                  </div>
                )}

                {/* BENCHMARK */}
                {activeTab === "benchmark" && (
                  <ReportBenchmark
                    analysis={analysis}
                  />
                )}

                {/* QUANTUM */}
                {activeTab === "quantum" && (
                  <ReportQuantum
                    analysis={analysis}
                  />
                )}

                {/* BIOMARKERS */}
                {activeTab === "biomarkers" && (
                  <ReportBiomarkers
                    analysis={analysis}
                  />
                )}

                {/* INPUT METRICS */}
                {activeTab === "input" && (
                  <ReportInputMetrics
                    analysis={analysis}
                    dataset={selectedDataset}
                  />
                )}
              </div>
            </div>
          </section>
        ) : (
          /* ===================================================
             EMPTY REPORT STATE
             =================================================== */

          <section className="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white px-5 py-8 text-center sm:px-8">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-xl">
              🧪
            </div>

            <h2 className="mt-4 text-base font-extrabold text-slate-800">
              Your research report will appear here
            </h2>

            <p className="mx-auto mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              Select a curated public dataset above and run BIOQURE analysis
              to populate the prediction, benchmark, quantum, biomarker, and
              preprocessing sections.
            </p>
          </section>
        )}
      </main>

      {/* =====================================================
          FOOTER
          ===================================================== */}

      <footer className="mx-auto max-w-[1500px] px-4 pb-8 pt-2 sm:px-6 lg:px-8">
        <div className="border-t border-slate-200 pt-5 text-center text-[11px] leading-5 text-slate-400">
          BIOQURE • Computational research decision-support interface •
          Public research datasets • Not a clinical diagnostic system
        </div>
      </footer>
    </div>
  );
}