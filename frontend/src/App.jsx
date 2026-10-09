import React, { memo, useMemo, useState } from "react";
import {
  Search,
  Bell,
  Cpu,
  Database,
  ScanSearch,
  SlidersHorizontal,
  Sparkles,
  Compass,
  BookOpen,
} from "lucide-react";
import DatasetPoolPanel from "./components/dataset/DatasetPoolPanel.jsx";
import ReportMetrics from "./components/report/ReportMetrics.jsx";
import ReportBenchmark from "./components/report/ReportBenchmark.jsx";
import ReportQuantum from "./components/report/ReportQuantum.jsx";
import ReportBiomarkers from "./components/report/ReportBiomarkers.jsx";
import ReportInputMetrics from "./components/report/ReportInputMetrics.jsx";
import { ChatAssistant } from "./ChatAssistant.jsx";
import ProductTour from "./TOUR/ProductTour.jsx";
import HelpMenu from "./TOUR/HelpMenu.jsx";
import { startProductTour } from "./TOUR/tourEvents.js";
import DnaHelixBase from "./DnaHelix.jsx";

// DnaHelix takes no props; memoizing stops it re-rendering on every dataset selection.
const DnaHelix = memo(DnaHelixBase);

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

function getBiomarkers(result, limit = 4) {
  const source =
    result?.biomarkers ??
    result?.biomarker_summary ??
    result?.result?.biomarkers ??
    [];

  const list = Array.isArray(source)
    ? source
    : Object.entries(source || {}).map(([gene, value]) => ({ gene, value }));

  return list.slice(0, limit).map((item, index) => ({
    gene: firstDefined(item?.gene, item?.gene_name, item?.feature, item?.name, `Feature ${index + 1}`),
    value: firstDefined(item?.value, item?.expression, item?.score, item?.importance, item?.signal),
  }));
}

function formatConfidence(value) {
  if (value === undefined || value === null || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  const pct = number >= 0 && number <= 1 ? number * 100 : number;
  return `${pct.toFixed(1)}%`;
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
    neutral: "border-[var(--bq-border-strong)] bg-[var(--bq-surface-alt)]/80 text-[var(--bq-text-dim)]",
    blue: "border-[var(--bq-accent)]/40 bg-[var(--bq-accent)]/10 text-[var(--bq-accent-strong)]",
    green: "border-[var(--bq-emerald)]/40 bg-[var(--bq-emerald)]/10 text-[var(--bq-emerald)]",
    purple: "border-violet-400/40 bg-violet-400/10 text-violet-300",
    amber: "border-[var(--bq-amber)]/45 bg-[var(--bq-amber)]/10 text-[var(--bq-amber)]",
  };

  return (
    <span
      className={`bq-display inline-flex items-center gap-1.5 border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.1em] ${
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
      data-active={active ? "true" : "false"}
      className="bq-sub-tab"
    >
      {children}
    </button>
  );
}

function SimpleView({ analysis, selectedModel, prediction, confidence, quantumState }) {
  const biomarkers = useMemo(() => getBiomarkers(analysis, 4), [analysis]);
  const confidenceText = formatConfidence(confidence);

  return (
    <div className="space-y-5">
      <div className="bq-hud p-5 sm:p-6">
        <span className="bq-panel-title -ml-5 -mt-5 sm:-ml-6">Final result</span>

        <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-2xl font-bold text-[var(--bq-text)]">{prediction}</div>
            <p className="mt-1 max-w-md text-sm leading-6 text-[var(--bq-text-dim)]">
              This is what the selected model classified the sample as, based on its gene-expression data.
            </p>
          </div>

          <div className="shrink-0 rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] px-5 py-4 text-center">
            <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
              Confidence level
            </div>
            <div className="bq-mono mt-1 text-2xl font-bold text-[var(--bq-accent-strong)]">
              {confidenceText}
            </div>
          </div>
        </div>
      </div>

      <div className="bq-hud p-5 sm:p-6">
        <span className="bq-panel-title -ml-5 -mt-5 sm:-ml-6">Key findings</span>
        <ul className="mt-4 space-y-2.5 text-sm leading-6 text-[var(--bq-text-dim)]">
          <li>
            • The model used for this result was <span className="font-semibold text-[var(--bq-text)]">{selectedModel}</span>.
          </li>
          <li>
            • Quantum computation was{" "}
            <span className="font-semibold text-[var(--bq-text)]">
              {quantumState === "Used" ? "used for this run" : quantumState === "Not used" ? "not used — a classical model handled this run" : "not reported"}
            </span>.
          </li>
          <li>
            • This result reflects the dataset selected above — it is one sample, not a population-wide finding.
          </li>
        </ul>
      </div>

      <div className="bq-hud p-5 sm:p-6">
        <span className="bq-panel-title -ml-5 -mt-5 sm:-ml-6">Important biomarkers</span>
        {biomarkers.length > 0 ? (
          <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
            {biomarkers.map((b, i) => (
              <div key={`${b.gene}-${i}`} className="flex items-center justify-between gap-3 rounded-lg border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] px-3.5 py-2.5">
                <span className="bq-mono text-xs font-semibold text-[var(--bq-text)]">{b.gene}</span>
                <span className="bq-mono text-xs text-[var(--bq-text-dim)]">
                  {typeof b.value === "number" ? b.value.toFixed(3) : String(b.value ?? "—")}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-[var(--bq-text-dim)]">No biomarker signals were returned for this run.</p>
        )}
        <p className="mt-3 text-xs leading-5 text-[var(--bq-text-faint)]">
          These are the genes that most influenced the model's prediction. See "Advanced Details" below for the full ranked list.
        </p>
      </div>

      <div className="bq-hud p-5 sm:p-6">
        <span className="bq-panel-title -ml-5 -mt-5 sm:-ml-6">Recommended next steps</span>
        <ul className="mt-4 space-y-2 text-sm leading-6 text-[var(--bq-text-dim)]">
          <li>• Open "Advanced Details" below to review the full model comparison and quantum run data.</li>
          <li>• Compare this result against another dataset to see how consistent the prediction is.</li>
          <li>• This is a research tool, not a diagnosis — any clinical decision should involve a qualified professional.</li>
        </ul>
      </div>
    </div>
  );
}

function ReadGuide() {
  const items = [
    ["Prediction", "The model's classification for this sample (e.g. tumour-like vs normal-like)."],
    ["Confidence", "How strongly the selected model supports that prediction, as a percentage."],
    ["Selected model", "Which model (classical or quantum) was used to produce the result shown."],
    ["Quantum path", "Whether the quantum circuit was actually used, or the platform fell back to a classical model."],
    ["Benchmark", "Accuracy, AUC, and F1 scores comparing every model on the same held-out data — higher is better for all three."],
    ["Biomarkers", "The genes/features that most influenced this prediction, ranked by signal strength."],
    ["Warnings", "Amber notices call out limitations or fallback behaviour; they don't mean the run failed."],
  ];

  return (
    <details className="bq-collapsible">
      <summary>
        <span className="flex items-center gap-2">
          <BookOpen className="size-4 text-[var(--bq-text-faint)]" aria-hidden />
          How to read this report
        </span>
        <span className="text-[11px] font-normal text-[var(--bq-text-faint)]">Click to expand</span>
      </summary>
      <dl className="grid gap-3 p-4 sm:grid-cols-2">
        {items.map(([term, desc]) => (
          <div key={term}>
            <dt className="text-xs font-bold text-[var(--bq-text)]">{term}</dt>
            <dd className="mt-0.5 text-xs leading-5 text-[var(--bq-text-dim)]">{desc}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function HudPanel({ title, action, className = "", children }) {
  return (
    <div className={`bq-hud-frame ${className}`}>
      <div className="bq-hud h-full">
        {(title || action) && (
          <div className="flex items-start justify-between gap-3">
            {title && <span className="bq-panel-title">{title}</span>}
            {action && <div className="p-2.5">{action}</div>}
          </div>
        )}
        {children}
      </div>
    </div>
  );
}

function StatTile({ value, label }) {
  return (
    <div className="bq-stat py-1">
      <div className="bq-display whitespace-nowrap text-[clamp(20px,1.7vw,26px)] font-semibold leading-none text-[var(--bq-text)]">{value}</div>
      <div className="mt-1.5 text-[10px] font-medium text-[var(--bq-text-faint)]">
        {label}
      </div>
    </div>
  );
}

function WorkflowStep({
  number,
  label,
  icon: Icon,
}) {
  return (
    <div className="bq-hud-frame group">
      <div className="bq-hud flex items-center gap-3 px-3 py-2.5 group-hover:translate-x-1">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center border border-[var(--bq-border-strong)] bg-[var(--bq-surface-alt)] text-[var(--bq-text-dim)] transition-colors group-hover:border-[var(--bq-accent)] group-hover:text-[var(--bq-accent-strong)]">
          {Icon ? <Icon className="size-4" aria-hidden /> : <span className="text-[10px] font-bold">{number}</span>}
        </span>

        <div className="min-w-0">
          <div className="bq-display text-[13px] font-semibold uppercase tracking-[0.08em] text-[var(--bq-text)]">
            {label}
          </div>
          <div className="bq-mono text-[10px] text-[var(--bq-text-faint)]">Step {number}</div>
        </div>
      </div>
    </div>
  );
}

function LogoMark() {
  return (
    <svg viewBox="0 0 40 40" className="h-10 w-10 shrink-0" aria-hidden>
      <defs>
        <linearGradient id="bq-logo-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#8db0ff" />
          <stop offset="1" stopColor="#3f6fe0" />
        </linearGradient>
      </defs>
      <path d="M9 4 C 30 14, 30 26, 9 36" fill="none" stroke="url(#bq-logo-grad)" strokeWidth="3" strokeLinecap="round" />
      <path d="M31 4 C 10 14, 10 26, 31 36" fill="none" stroke="url(#bq-logo-grad)" strokeWidth="3" strokeLinecap="round" />
      <path d="M14 10 H26 M14 30 H26" stroke="#8db0ff" strokeOpacity="0.55" strokeWidth="1.5" />
    </svg>
  );
}

const NAV_ITEMS = [
  { id: "overview", label: "Overview" },
  { id: "datasets", label: "Dataset Pool" },
  { id: "report", label: "Research Report" },
];

/* =========================================================
   APP
   ========================================================= */

export default function App() {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [reportMode, setReportMode] = useState("simple");
  const [activeNav, setActiveNav] = useState("overview");

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
    setReportMode("simple");
  }

  function handleNav(id) {
    setActiveNav(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="relative min-h-screen text-[var(--bq-text)]">
      {/* =====================================================
          HEADER
          ===================================================== */}

      <header className="sticky top-0 z-40 border-b border-[var(--bq-border)] bg-[var(--bq-bg)]/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <LogoMark />

            <div className="min-w-0">
              <div className="bq-display truncate text-xl font-bold tracking-[0.04em]">
                <span className="text-[var(--bq-text)]">BIOQU</span>
                <span className="text-[var(--bq-accent)]">RE</span>
              </div>

              <div className="hidden truncate text-[9px] font-semibold uppercase tracking-[0.2em] text-[var(--bq-text-faint)] sm:block xl:hidden 2xl:block">
                Breast Cancer Research Intelligence
              </div>
            </div>
          </div>

          <nav className="hidden items-center xl:flex" aria-label="Sections">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleNav(item.id)}
                data-active={activeNav === item.id ? "true" : "false"}
                className="bq-nav-tab"
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            <div className="bq-hud hidden w-64 items-center gap-2 px-3 py-2.5 lg:flex">
              <Search className="size-4 shrink-0 text-[var(--bq-text-faint)]" aria-hidden />
              <input
                type="text"
                placeholder="SEARCH DATASETS, GENES…"
                className="bq-display w-full bg-transparent text-xs tracking-[0.08em] text-[var(--bq-text)] outline-none placeholder:text-[var(--bq-text-faint)]"
              />
            </div>

            <div className="hidden items-center gap-2 2xl:flex">
              <Badge tone="blue">RNA-seq</Badge>
              <Badge tone="purple">Quantum ML</Badge>
            </div>

            <Badge tone={analysis ? "green" : "neutral"}>
              {analysis ? "Analysis available" : "Research mode"}
            </Badge>

            <button
              type="button"
              className="bq-icon-btn"
              aria-label="Notifications"
            >
              <Bell className="size-4" aria-hidden />
            </button>

            <HelpMenu />
          </div>
        </div>
      </header>

      {/* =====================================================
          MAIN
          ===================================================== */}

      <main className="relative z-10 mx-auto max-w-[1500px] px-4 py-8 sm:px-6 lg:px-8">
        {/* ===================================================
            HERO
            =================================================== */}

        <section
          id="overview"
          data-tour="dashboard"
          className="bq-grid-bg bq-rise relative scroll-mt-24 overflow-hidden rounded-3xl border border-[var(--bq-border)] bg-[var(--bq-bg)]/70"
        >
          <div className="grid gap-7 px-5 py-8 lg:grid-cols-[0.95fr_1.15fr_0.85fr] lg:px-8 lg:py-10">
            <div className="relative z-10 flex flex-col lg:py-4">
              <div className="bq-rise bq-delay-1 flex flex-wrap items-center gap-2">
                <Badge tone="blue">
                  <span className="bq-live-dot" aria-hidden />
                  ACTIVE · PUBLIC DATA
                </Badge>
                <Badge>BIOQURE PLATFORM</Badge>
                <button type="button" onClick={startProductTour} className="bq-tour-launch">
                  <Compass className="size-3.5" aria-hidden />
                  Take Product Tour
                </button>
              </div>

              <h1 className="bq-rise bq-delay-2 mt-5 max-w-4xl text-3xl font-semibold uppercase leading-[1.05] tracking-[0.02em] text-[var(--bq-text)] sm:text-4xl xl:text-[44px]">
                Breast-cancer expression analysis with classical and quantum
                machine learning.
              </h1>

              <p className="bq-rise bq-delay-3 mt-4 max-w-3xl text-sm leading-7 text-[var(--bq-text-dim)]">
                Explore curated public expression datasets, apply the BIOQURE
                preprocessing pipeline, and inspect model inference,
                benchmark information, biomarker signals, and quantum runtime
                metadata from a single research workspace.
              </p>

            </div>

            <div className="bq-rise bq-delay-2 relative flex min-h-[520px] md:min-h-[600px]">
              <DnaHelix />
            </div>

            <div className="relative z-10 flex flex-col gap-5">
              <HudPanel
                className="bq-rise bq-delay-3"
                title="Platform"
                action={
                  <span className="flex size-8 items-center justify-center border border-[var(--bq-border-strong)] bg-[var(--bq-accent)]/10 text-[var(--bq-accent-strong)]">
                    <Sparkles className="size-4" aria-hidden />
                  </span>
                }
              >
                <div className="grid grid-cols-2 gap-x-4 gap-y-5 px-5 pb-5 pt-3">
                  <StatTile value="TCGA-BRCA" label="Dataset pool" />
                  <StatTile value="4" label="Classical models" />
                  <StatTile value="6–8" label="Qubits used" />
                  <StatTile value="1024" label="Shots / run" />
                </div>
              </HudPanel>

              <HudPanel className="bq-rise bq-delay-4" title="Workflow">
                <div className="space-y-2.5 p-4 pt-3">
                  <WorkflowStep
                    number="01"
                    label="Select dataset"
                    icon={Database}
                  />

                  <WorkflowStep
                    number="02"
                    label="Preprocess expression"
                    icon={SlidersHorizontal}
                  />

                  <WorkflowStep
                    number="03"
                    label="Run model inference"
                    icon={Cpu}
                  />

                  <WorkflowStep
                    number="04"
                    label="Inspect research output"
                    icon={ScanSearch}
                  />
                </div>
              </HudPanel>
            </div>
          </div>
        </section>

        {/* ===================================================
            DATASET WORKSPACE
            =================================================== */}

        <section id="datasets" className="bq-rise bq-delay-3 mt-8 scroll-mt-24">
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
          <section id="report" data-tour="report" className="bq-rise mt-8 scroll-mt-24">
            <div className="overflow-hidden rounded-3xl border border-[var(--bq-border)] bg-[var(--bq-surface)]/90 backdrop-blur-sm">
              {/* Report header */}
              <div className="border-b border-[var(--bq-border)] px-5 py-5 sm:px-6">
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

                    <h2 className="mt-2 text-3xl font-semibold uppercase tracking-[0.04em] text-[var(--bq-text)]">
                      BIOQURE Research Report
                    </h2>

                    <p className="mt-1 text-sm text-[var(--bq-text-dim)]">
                      Model output and runtime information for the selected
                      public dataset.
                    </p>
                  </div>

                  <div className="rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] px-4 py-3">
                    <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--bq-text-faint)]">
                      Prediction
                    </div>

                    <div className="mt-1 text-sm font-extrabold text-[var(--bq-text)]">
                      {prediction}
                    </div>

                    <div className="mt-1 text-[10px] text-[var(--bq-text-faint)]">
                      Model: {selectedModel}
                    </div>
                  </div>
                </div>

                {/* =================================================
                    SIMPLE / ADVANCED TOGGLE
                    ================================================= */}

                <div className="mt-5 inline-flex gap-1 rounded-lg border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] p-1">
                  <button
                    type="button"
                    onClick={() => setReportMode("simple")}
                    className="bq-sub-tab"
                    data-active={reportMode === "simple" ? "true" : "false"}
                  >
                    Simple view
                  </button>
                  <button
                    type="button"
                    onClick={() => setReportMode("advanced")}
                    className="bq-sub-tab"
                    data-active={reportMode === "advanced" ? "true" : "false"}
                  >
                    Advanced details
                  </button>
                </div>
              </div>

              <div className="px-5 pt-5 sm:px-6">
                <ReadGuide />
              </div>

              {/* =================================================
                  REPORT CONTENT
                  ================================================= */}

              <div className="p-5 sm:p-6">
                {reportMode === "simple" && (
                  <SimpleView
                    analysis={analysis}
                    selectedModel={selectedModel}
                    prediction={prediction}
                    confidence={confidence}
                    quantumState={quantumState}
                  />
                )}

                {reportMode === "advanced" && (
                  <div className="space-y-5">
                    <div data-tour="report-tabs" className="flex flex-wrap gap-1 border-b border-[var(--bq-border)] pb-2">
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

                    {/* OVERVIEW */}
                    {activeTab === "overview" && (
                      <div className="space-y-5">
                        <ReportMetrics
                          analysis={analysis}
                          dataset={selectedDataset}
                        />

                        <div className="grid gap-5 lg:grid-cols-2">
                          <div className="bq-hud p-5">
                            <span className="bq-panel-title -ml-5 -mt-5">Model execution</span>

                            <div className="mt-4 space-y-3">
                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-[var(--bq-text-dim)]">
                                  Selected model
                                </span>

                                <span className="text-sm font-bold text-[var(--bq-text)]">
                                  {selectedModel}
                                </span>
                              </div>

                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-[var(--bq-text-dim)]">
                                  Prediction
                                </span>

                                <span className="text-sm font-bold text-[var(--bq-text)]">
                                  {prediction}
                                </span>
                              </div>

                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-[var(--bq-text-dim)]">
                                  Confidence
                                </span>

                                <span className="text-sm font-bold text-[var(--bq-text)]">
                                  {confidence !== undefined &&
                                  confidence !== null
                                    ? confidence
                                    : "—"}
                                </span>
                              </div>

                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-[var(--bq-text-dim)]">
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

                          <div className="bq-hud p-5">
                            <span className="bq-panel-title -ml-5 -mt-5">Dataset context</span>

                            <div className="mt-4 space-y-3">
                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-[var(--bq-text-dim)]">
                                  Dataset ID
                                </span>

                                <span className="font-mono text-xs font-bold text-[var(--bq-text)]">
                                  {selectedDataset?.id || "—"}
                                </span>
                              </div>

                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-[var(--bq-text-dim)]">
                                  Project
                                </span>

                                <span className="text-sm font-bold text-[var(--bq-text)]">
                                  {selectedDataset?.project || "—"}
                                </span>
                              </div>

                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-[var(--bq-text-dim)]">
                                  Source
                                </span>

                                <span className="text-sm font-bold text-[var(--bq-text)]">
                                  {selectedDataset?.source || "—"}
                                </span>
                              </div>

                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-[var(--bq-text-dim)]">
                                  Data type
                                </span>

                                <span className="text-sm font-bold text-[var(--bq-text)]">
                                  {selectedDataset?.dataType || "—"}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="border border-[var(--bq-amber)]/40 bg-[var(--bq-amber)]/10 p-4">
                          <div className="text-xs font-bold text-amber-300">
                            Research-use notice
                          </div>

                          <p className="mt-1 text-xs leading-5 text-amber-300">
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
                )}
              </div>
            </div>
          </section>
        ) : (
          /* ===================================================
             EMPTY REPORT STATE
             =================================================== */

          <section id="report" data-tour="report" className="bq-hud bq-rise bq-delay-4 mt-8 scroll-mt-24 px-5 py-12 text-center sm:px-8">
            <div className="mx-auto flex h-12 w-12 items-center justify-center border border-[var(--bq-border-strong)] bg-[var(--bq-accent)]/10 text-[var(--bq-accent-strong)]">
              <ScanSearch className="size-5" aria-hidden />
            </div>

            <h2 className="mt-4 text-lg font-semibold uppercase tracking-[0.08em] text-[var(--bq-text)]">
              Your research report will appear here
            </h2>

            <p className="mx-auto mt-1 max-w-2xl text-sm leading-6 text-[var(--bq-text-dim)]">
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

      <footer className="relative z-10 mx-auto max-w-[1500px] px-4 pb-8 pt-2 sm:px-6 lg:px-8">
        <div className="border-t border-[var(--bq-border)] pt-5 text-center text-[11px] leading-5 text-[var(--bq-text-faint)]">
          BIOQURE • Computational research decision-support interface •
          Public research datasets • Not a clinical diagnostic system
          <button type="button" onClick={startProductTour} className="bq-tour-link ml-2">
            Take Product Tour
          </button>
        </div>
      </footer>

      <ChatAssistant hasResult={!!analysis} />
      <ProductTour />
    </div>
  );
}