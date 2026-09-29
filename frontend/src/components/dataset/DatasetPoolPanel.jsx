import React, { useEffect, useMemo, useState } from "react";
import {
  analyzePublicDataset,
  getBIOQUREStatus,
  getPublicDataset,
  listPublicDatasets,
  savePublicDataset,
} from "../../services/datasetsApi.js";

/* =========================================================
   HELPERS
   ========================================================= */

function firstDefined(...values) {
  return values.find(
    (value) => value !== undefined && value !== null && value !== ""
  );
}

function normalizeDataset(item, index = 0) {
  const id = firstDefined(
    item?.dataset_id,
    item?.datasetId,
    item?.id,
    item?.uuid,
    `BRCA_${String(index + 1).padStart(3, "0")}`
  );

  return {
    ...item,
    id,
    dataset_id: id,
    name: firstDefined(
      item?.name,
      item?.title,
      item?.dataset_name,
      id
    ),
    description: firstDefined(
      item?.description,
      item?.summary,
      item?.details,
      "Public breast-cancer expression dataset prepared for BIOQURE analysis."
    ),
    source: firstDefined(
      item?.source,
      item?.repository,
      item?.database,
      "TCGA / GDC"
    ),
    project: firstDefined(
      item?.project,
      item?.project_id,
      item?.program,
      "TCGA-BRCA"
    ),
    sampleCount: firstDefined(
      item?.sample_count,
      item?.sampleCount,
      item?.samples,
      item?.n_samples,
      item?.n
    ),
    geneCount: firstDefined(
      item?.gene_count,
      item?.geneCount,
      item?.genes,
      item?.n_genes
    ),
    fileName: firstDefined(
      item?.expression_file,
      item?.expression_filename,
      item?.file_name,
      item?.filename,
      "expression.tsv"
    ),
    access: firstDefined(
      item?.access,
      item?.access_level,
      "Public"
    ),
    dataType: firstDefined(
      item?.data_type,
      item?.dataType,
      item?.expression_type,
      "RNA-seq expression"
    ),
  };
}

function normalizeDatasetResponse(response) {
  const items =
    response?.datasets ??
    response?.items ??
    response?.results ??
    response?.data ??
    response;

  if (!Array.isArray(items)) {
    return [];
  }

  return items.map((item, index) => normalizeDataset(item, index));
}

function formatNumber(value) {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return String(value);
  }

  return new Intl.NumberFormat("en-IN").format(number);
}

function formatPercent(value) {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return String(value);
  }

  const normalized =
    number >= 0 && number <= 1 ? number * 100 : number;

  return `${normalized.toFixed(1)}%`;
}

function getStatusTone(status) {
  const value = String(status || "").toLowerCase();

  if (
    value.includes("ready") ||
    value.includes("success") ||
    value.includes("available") ||
    value.includes("complete")
  ) {
    return "success";
  }

  if (
    value.includes("error") ||
    value.includes("fail") ||
    value.includes("unavailable")
  ) {
    return "error";
  }

  if (
    value.includes("running") ||
    value.includes("loading") ||
    value.includes("processing")
  ) {
    return "warning";
  }

  return "neutral";
}

function Badge({ children, tone = "neutral" }) {
  const tones = {
    neutral:
      "border-slate-200 bg-slate-50 text-slate-600",
    success:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning:
      "border-amber-200 bg-amber-50 text-amber-700",
    error:
      "border-red-200 bg-red-50 text-red-700",
    blue:
      "border-blue-200 bg-blue-50 text-blue-700",
    purple:
      "border-violet-200 bg-violet-50 text-violet-700",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${tones[tone] || tones.neutral}`}
    >
      {children}
    </span>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
        {label}
      </div>
      <div className="mt-0.5 text-sm font-bold text-slate-800">
        {value}
      </div>
    </div>
  );
}

/* =========================================================
   MAIN COMPONENT
   ========================================================= */

export default function DatasetPoolPanel({
  onDatasetSelect,
  onAnalysisComplete,
  selectedDatasetId,
  compact = false,
  className = "",
}) {
  const [datasets, setDatasets] = useState([]);
  const [selectedId, setSelectedId] = useState(
    selectedDatasetId || ""
  );

  const [selectedDataset, setSelectedDataset] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const [error, setError] = useState("");
  const [analysisError, setAnalysisError] = useState("");

  const [backendStatus, setBackendStatus] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  /* -------------------------------------------------------
     Load datasets + backend status
     ------------------------------------------------------- */

  async function loadDatasets() {
    setLoading(true);
    setError("");

    try {
      const response = await listPublicDatasets({
        limit: 100,
      });

      const normalized = normalizeDatasetResponse(response);

      setDatasets(normalized);

      const preferredId =
        selectedDatasetId ||
        normalized[0]?.id ||
        "";

      if (preferredId) {
        setSelectedId(preferredId);
      }
    } catch (err) {
      setError(
        err?.message ||
          "Unable to load the BIOQURE public dataset collection."
      );
      setDatasets([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadBackendStatus() {
    try {
      const response = await getBIOQUREStatus();
      setBackendStatus(response);
    } catch {
      setBackendStatus(null);
    }
  }

  useEffect(() => {
    loadDatasets();
    loadBackendStatus();
  }, []);

  useEffect(() => {
    if (selectedDatasetId && selectedDatasetId !== selectedId) {
      setSelectedId(selectedDatasetId);
    }
  }, [selectedDatasetId, selectedId]);

  /* -------------------------------------------------------
     Load selected dataset details
     ------------------------------------------------------- */

  async function loadDatasetDetails(datasetId) {
    if (!datasetId) return;

    setLoadingDetail(true);
    setAnalysis(null);
    setAnalysisError("");

    try {
      const response = await getPublicDataset(datasetId);

      const normalized = normalizeDataset(response);

      setSelectedDataset(normalized);

      if (onDatasetSelect) {
        onDatasetSelect(normalized);
      }
    } catch (err) {
      setSelectedDataset(
        datasets.find((dataset) => dataset.id === datasetId) || null
      );

      setError(
        err?.message ||
          "Unable to load dataset details."
      );
    } finally {
      setLoadingDetail(false);
    }
  }

  useEffect(() => {
    if (!selectedId) {
      setSelectedDataset(null);
      return;
    }

    loadDatasetDetails(selectedId);
  }, [selectedId]);

  /* -------------------------------------------------------
     Filtered collection
     ------------------------------------------------------- */

  const filteredDatasets = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return datasets;
    }

    return datasets.filter((dataset) => {
      const searchable = [
        dataset.id,
        dataset.name,
        dataset.description,
        dataset.source,
        dataset.project,
        dataset.dataType,
        dataset.fileName,
        dataset.access,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchable.includes(query);
    });
  }, [datasets, search]);

  /* -------------------------------------------------------
     Select dataset
     ------------------------------------------------------- */

  function handleSelect(dataset) {
    setSelectedId(dataset.id);
    setAnalysis(null);
    setAnalysisError("");
  }

  /* -------------------------------------------------------
     Analyze dataset
     ------------------------------------------------------- */

  async function handleAnalyze() {
    if (!selectedId || analyzing) {
      return;
    }

    setAnalyzing(true);
    setAnalysis(null);
    setAnalysisError("");

    try {
      const result = await analyzePublicDataset(selectedId, {
        return_details: true,
      });

      setAnalysis(result);

      if (onAnalysisComplete) {
        onAnalysisComplete(result, selectedDataset);
      }
    } catch (err) {
      setAnalysisError(
        err?.message ||
          "BIOQURE analysis could not be completed."
      );
    } finally {
      setAnalyzing(false);
    }
  }

  /* -------------------------------------------------------
     Download
     ------------------------------------------------------- */

  async function handleDownload() {
    if (!selectedId || downloading) {
      return;
    }

    setDownloading(true);

    try {
      await savePublicDataset(
        selectedId,
        selectedDataset?.fileName
      );
    } catch (err) {
      setError(
        err?.message ||
          "Dataset download failed."
      );
    } finally {
      setDownloading(false);
    }
  }

  /* -------------------------------------------------------
     Analysis helpers
     ------------------------------------------------------- */

  const prediction = firstDefined(
    analysis?.prediction,
    analysis?.result?.prediction,
    analysis?.classification,
    analysis?.result?.classification
  );

  const predictedLabel = firstDefined(
    prediction?.label,
    prediction?.class_label,
    prediction?.prediction,
    analysis?.predicted_label,
    analysis?.predicted_class,
    analysis?.label,
    typeof prediction === "string" ? prediction : null
  );

  const predictedProbability = firstDefined(
    prediction?.probability,
    prediction?.confidence,
    prediction?.score,
    analysis?.probability,
    analysis?.confidence,
    analysis?.score
  );

  const selectedModel = firstDefined(
    analysis?.model_selection?.selected_model,
    analysis?.model_selection?.model,
    analysis?.selected_model,
    analysis?.model,
    analysis?.inference?.selected_model
  );

  const quantumUsed = firstDefined(
    analysis?.quantum?.used,
    analysis?.quantum_used,
    analysis?.runtime?.quantum_used,
    analysis?.inference?.quantum_used
  );

  const fallbackUsed = firstDefined(
    analysis?.fallback_used,
    analysis?.runtime?.fallback_used,
    analysis?.inference?.fallback_used
  );

  const biomarkerSummary =
    analysis?.biomarkers ??
    analysis?.biomarker_summary ??
    analysis?.result?.biomarkers ??
    [];

  const biomarkerRows = Array.isArray(biomarkerSummary)
    ? biomarkerSummary
    : Object.entries(biomarkerSummary || {}).map(
        ([gene, value]) => ({
          gene,
          value,
        })
      );

  /* -------------------------------------------------------
     Compact mode
     ------------------------------------------------------- */

  if (compact) {
    return (
      <div
        className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
              BIOQURE dataset
            </div>

            <div className="mt-1 text-sm font-bold text-slate-800">
              {selectedDataset?.name ||
                selectedId ||
                "No dataset selected"}
            </div>
          </div>

          {backendStatus && (
            <Badge
              tone={
                getStatusTone(
                  firstDefined(
                    backendStatus?.status,
                    backendStatus?.state
                  )
                ) === "success"
                  ? "success"
                  : "neutral"
              }
            >
              {firstDefined(
                backendStatus?.status,
                backendStatus?.state,
                "Ready"
              )}
            </Badge>
          )}
        </div>

        {selectedDataset && (
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Stat
              label="Samples"
              value={formatNumber(selectedDataset.sampleCount)}
            />
            <Stat
              label="Genes"
              value={formatNumber(selectedDataset.geneCount)}
            />
          </div>
        )}

        <button
          type="button"
          onClick={handleAnalyze}
          disabled={!selectedId || analyzing}
          className="mt-3 w-full rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {analyzing ? "Analyzing…" : "Run BIOQURE Analysis"}
        </button>
      </div>
    );
  }

  /* -------------------------------------------------------
     FULL PANEL
     ------------------------------------------------------- */

  return (
    <section
      className={`rounded-3xl border border-slate-200 bg-slate-50 shadow-sm ${className}`}
    >
      {/* Header */}
      <div className="border-b border-slate-200 bg-white px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-extrabold tracking-tight text-slate-900">
                Public Research Datasets
              </h2>

              <Badge tone="blue">BIOQURE</Badge>
              <Badge tone="purple">TCGA / GDC</Badge>
            </div>

            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
              Select a curated public breast-cancer expression dataset,
              inspect its metadata, and send the selected dataset through
              the BIOQURE inference pipeline.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {backendStatus && (
              <Badge
                tone={
                  getStatusTone(
                    firstDefined(
                      backendStatus?.status,
                      backendStatus?.state
                    )
                  ) === "success"
                    ? "success"
                    : "neutral"
                }
              >
                Backend{" "}
                {firstDefined(
                  backendStatus?.status,
                  backendStatus?.state,
                  "available"
                )}
              </Badge>
            )}

            <button
              type="button"
              onClick={() => {
                loadDatasets();
                loadBackendStatus();
              }}
              disabled={loading}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 disabled:opacity-50"
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search dataset ID, project, source, or description…"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:bg-white"
            />
          </div>

          <div className="flex items-center rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs font-semibold text-slate-500">
            {filteredDatasets.length} dataset
            {filteredDatasets.length === 1 ? "" : "s"}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-5 mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:mx-6">
          <div className="font-semibold">Dataset service message</div>
          <div className="mt-1">{error}</div>
        </div>
      )}

      {/* Main grid */}
      <div className="grid gap-5 p-5 sm:p-6 xl:grid-cols-[1.15fr_0.85fr]">
        {/* Dataset collection */}
        <div className="min-w-0">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-bold text-slate-800">
                Curated collection
              </div>

              <div className="text-xs text-slate-500">
                Public datasets available to BIOQURE
              </div>
            </div>

            <Badge>
              {datasets.length
                ? `${datasets.length} loaded`
                : "No datasets"}
            </Badge>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((item) => (
                <div
                  key={item}
                  className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white"
                />
              ))}
            </div>
          ) : filteredDatasets.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-lg">
                🧬
              </div>

              <div className="mt-4 text-sm font-bold text-slate-800">
                No public datasets found
              </div>

              <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-slate-500">
                The BIOQURE public collection is empty or the current search
                does not match any dataset.
              </p>

              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  className="mt-4 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Clear search
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredDatasets.map((dataset) => {
                const active = dataset.id === selectedId;

                return (
                  <button
                    type="button"
                    key={dataset.id}
                    onClick={() => handleSelect(dataset)}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      active
                        ? "border-slate-400 bg-white shadow-sm ring-1 ring-slate-300"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm"
                    }`}
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-lg bg-slate-900 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.08em] text-white">
                            {dataset.id}
                          </span>

                          <Badge tone="success">
                            {dataset.access}
                          </Badge>
                        </div>

                        <div className="mt-2 truncate text-sm font-bold text-slate-800">
                          {dataset.name}
                        </div>

                        <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                          {dataset.description}
                        </div>
                      </div>

                      <div className="shrink-0 text-xs text-slate-400">
                        {dataset.project}
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="rounded-lg bg-slate-50 px-2.5 py-1.5 text-[11px] font-medium text-slate-500">
                        {dataset.dataType}
                      </span>

                      <span className="rounded-lg bg-slate-50 px-2.5 py-1.5 text-[11px] font-medium text-slate-500">
                        Samples: {formatNumber(dataset.sampleCount)}
                      </span>

                      <span className="rounded-lg bg-slate-50 px-2.5 py-1.5 text-[11px] font-medium text-slate-500">
                        Genes: {formatNumber(dataset.geneCount)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Dataset details / analysis */}
        <div className="min-w-0">
          <div className="mb-3">
            <div className="text-sm font-bold text-slate-800">
              Dataset workspace
            </div>

            <div className="text-xs text-slate-500">
              Metadata, inference controls, and returned analysis
            </div>
          </div>

          {!selectedId ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
              <div className="text-3xl">🧬</div>
              <div className="mt-3 text-sm font-bold text-slate-800">
                Select a dataset
              </div>
              <div className="mt-1 text-xs text-slate-500">
                Choose a dataset from the collection to view details.
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Dataset detail card */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                {loadingDetail ? (
                  <div className="space-y-3">
                    <div className="h-5 w-2/3 animate-pulse rounded bg-slate-100" />
                    <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                    <div className="h-4 w-5/6 animate-pulse rounded bg-slate-100" />
                    <div className="grid grid-cols-2 gap-2 pt-2">
                      <div className="h-16 animate-pulse rounded-xl bg-slate-100" />
                      <div className="h-16 animate-pulse rounded-xl bg-slate-100" />
                    </div>
                  </div>
                ) : selectedDataset ? (
                  <>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone="blue">
                            {selectedDataset.id}
                          </Badge>

                          <Badge tone="success">
                            {selectedDataset.access}
                          </Badge>
                        </div>

                        <h3 className="mt-2 break-words text-lg font-extrabold text-slate-900">
                          {selectedDataset.name}
                        </h3>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          setShowDetails((value) => !value)
                        }
                        className="shrink-0 rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        {showDetails ? "Hide JSON" : "View JSON"}
                      </button>
                    </div>

                    <p className="mt-3 text-sm leading-6 text-slate-500">
                      {selectedDataset.description}
                    </p>

                    <div className="mt-4 grid grid-cols-2 gap-2">
                      <Stat
                        label="Source"
                        value={selectedDataset.source}
                      />

                      <Stat
                        label="Project"
                        value={selectedDataset.project}
                      />

                      <Stat
                        label="Samples"
                        value={formatNumber(
                          selectedDataset.sampleCount
                        )}
                      />

                      <Stat
                        label="Features"
                        value={formatNumber(
                          selectedDataset.geneCount
                        )}
                      />
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge>
                        {selectedDataset.dataType}
                      </Badge>

                      <Badge>
                        {selectedDataset.fileName}
                      </Badge>
                    </div>

                    {showDetails && (
                      <pre className="mt-4 max-h-72 overflow-auto rounded-xl bg-slate-950 p-4 text-[10px] leading-5 text-slate-200">
                        {JSON.stringify(
                          selectedDataset,
                          null,
                          2
                        )}
                      </pre>
                    )}

                    <div className="mt-5 flex flex-col gap-2 sm:flex-row">
                      <button
                        type="button"
                        onClick={handleAnalyze}
                        disabled={analyzing}
                        className="flex-1 rounded-xl bg-slate-900 px-4 py-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {analyzing
                          ? "Running BIOQURE…"
                          : "Run BIOQURE Analysis"}
                      </button>

                      <button
                        type="button"
                        onClick={handleDownload}
                        disabled={downloading}
                        className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {downloading
                          ? "Downloading…"
                          : "Download Dataset"}
                      </button>
                    </div>

                    {analysisError && (
                      <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-3 text-xs leading-5 text-red-700">
                        {analysisError}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-sm text-slate-500">
                    Dataset details are unavailable.
                  </div>
                )}
              </div>

              {/* Analysis result */}
              {analysis && (
                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-bold text-slate-800">
                        Analysis result
                      </div>

                      <div className="mt-0.5 text-xs text-slate-500">
                        Returned by the BIOQURE inference service
                      </div>
                    </div>

                    <Badge tone="success">
                      Complete
                    </Badge>
                  </div>

                  {/* Prediction */}
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                        Prediction
                      </div>

                      <div className="mt-1 text-lg font-extrabold text-slate-900">
                        {predictedLabel || "—"}
                      </div>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                        Confidence
                      </div>

                      <div className="mt-1 text-lg font-extrabold text-slate-900">
                        {formatPercent(predictedProbability)}
                      </div>
                    </div>
                  </div>

                  {/* Runtime/model */}
                  <div className="mt-2 grid gap-2 sm:grid-cols-3">
                    <Stat
                      label="Selected model"
                      value={selectedModel || "—"}
                    />

                    <Stat
                      label="Quantum"
                      value={
                        quantumUsed === true
                          ? "Used"
                          : quantumUsed === false
                            ? "Not used"
                            : "—"
                      }
                    />

                    <Stat
                      label="Fallback"
                      value={
                        fallbackUsed === true
                          ? "Used"
                          : fallbackUsed === false
                            ? "Not used"
                            : "—"
                      }
                    />
                  </div>

                  {/* Biomarkers */}
                  {biomarkerRows.length > 0 && (
                    <div className="mt-5">
                      <div className="text-xs font-bold uppercase tracking-[0.1em] text-slate-400">
                        Biomarker signals
                      </div>

                      <div className="mt-2 overflow-hidden rounded-xl border border-slate-200">
                        <div className="divide-y divide-slate-200">
                          {biomarkerRows
                            .slice(0, 8)
                            .map((row, index) => {
                              const gene = firstDefined(
                                row?.gene,
                                row?.gene_name,
                                row?.feature,
                                row?.name,
                                Object.keys(row || {})[0],
                                `Feature ${index + 1}`
                              );

                              const value = firstDefined(
                                row?.value,
                                row?.expression,
                                row?.score,
                                row?.importance,
                                row?.signal,
                                Object.values(row || {})[1]
                              );

                              return (
                                <div
                                  key={`${gene}-${index}`}
                                  className="flex items-center justify-between gap-4 px-3 py-2.5"
                                >
                                  <span className="font-mono text-xs font-semibold text-slate-700">
                                    {gene}
                                  </span>

                                  <span className="text-xs font-semibold text-slate-500">
                                    {typeof value === "number"
                                      ? value.toFixed(4)
                                      : String(value ?? "—")}
                                  </span>
                                </div>
                              );
                            })}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Raw response */}
                  <details className="mt-4">
                    <summary className="cursor-pointer text-xs font-semibold text-slate-500">
                      View complete analysis response
                    </summary>

                    <pre className="mt-2 max-h-80 overflow-auto rounded-xl bg-slate-950 p-4 text-[10px] leading-5 text-slate-200">
                      {JSON.stringify(
                        analysis,
                        null,
                        2
                      )}
                    </pre>
                  </details>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-slate-200 bg-white px-5 py-4 sm:px-6">
        <div className="flex flex-col gap-2 text-[11px] leading-5 text-slate-400 sm:flex-row sm:items-center sm:justify-between">
          <span>
            BIOQURE is a research decision-support interface.
          </span>

          <span>
            Dataset selection does not constitute a clinical diagnosis.
          </span>
        </div>
      </div>
    </section>
  );
}