import { API_BASE } from "../config.js";

const BASE = `${API_BASE}/api/v1`;

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  let payload;

  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    let message = "Request failed.";

    if (typeof payload === "string" && payload.trim()) {
      message = payload;
    } else if (payload?.detail) {
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else {
        message = JSON.stringify(payload.detail);
      }
    } else if (payload?.message) {
      message = payload.message;
    }

    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });

  return parseResponse(response);
}

/* =========================================================
   BIOQURE PUBLIC DATASET API
   ========================================================= */

/**
 * Get all curated public datasets.
 *
 * GET /bioqure/datasets/public
 */
export async function listPublicDatasets(options = {}) {
  const response = await request("/demo-samples", { method: "GET" });
  const query = String(options.search || "").trim().toLowerCase();
  const samples = (response?.samples || []).filter((sample) => {
    return !query || [sample.demo_id, sample.display_name, sample.sample_type]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(query);
  });
  return {
    datasets: samples.map((sample) => ({
      dataset_id: sample.demo_id,
      name: sample.display_name,
      description: "Training-split TCGA-BRCA STAR-counts sample.",
      source: "TCGA / GDC",
      project: "TCGA-BRCA",
      sample_type: sample.sample_type,
      split: sample.split,
      file_name: `${sample.demo_id}.rna_seq.augmented_star_gene_counts.tsv`,
      access: "Public",
      data_type: "RNA-seq expression",
      size_bytes: sample.size_bytes,
      file_sha256: sample.file_sha256,
      biomarkers_available: sample.biomarkers_available,
    })),
  };
}

/**
 * Get details for one public dataset.
 *
 * GET /bioqure/datasets/public/{dataset_id}
 */
export async function getPublicDataset(datasetId) {
  if (!datasetId) {
    throw new Error("Dataset ID is required.");
  }

  const response = await listPublicDatasets();
  const dataset = response.datasets.find((item) => item.dataset_id === datasetId);
  if (!dataset) throw new Error("Public sample was not found.");
  return dataset;
}

/**
 * Download a public dataset.
 *
 * Returns the raw Response so the caller can create a Blob/download.
 *
 * GET /bioqure/datasets/public/{dataset_id}/download
 */
export async function downloadPublicDataset(datasetId) {
  if (!datasetId) {
    throw new Error("Dataset ID is required.");
  }

  throw new Error("Public samples are resolved server-side and are not downloaded to the browser.");
}

/**
 * Analyze one public dataset.
 *
 * POST /bioqure/datasets/public/{dataset_id}/analyze
 */
export async function analyzePublicDataset(datasetId, options = {}) {
  if (!datasetId) {
    throw new Error("Dataset ID is required.");
  }

  return request(`/predict/demo/${encodeURIComponent(datasetId)}`, {
    method: "POST",
    body: JSON.stringify({ ...options }),
  });
}

/**
 * Get BIOQURE backend/model runtime status.
 *
 * GET /bioqure/status
 */
export async function getBIOQUREStatus() {
  return request("/health", {
    method: "GET",
  });
}

/* =========================================================
   CONVENIENCE HELPERS
   ========================================================= */

/**
 * Get a dataset and its analysis together.
 *
 * This is a frontend convenience function.
 */
export async function getDatasetReport(datasetId, options = {}) {
  const [dataset, analysis] = await Promise.all([
    getPublicDataset(datasetId),
    analyzePublicDataset(datasetId, options),
  ]);

  return {
    dataset,
    analysis,
  };
}

/**
 * Trigger analysis and normalize the returned shape.
 *
 * Keeps the component code simple even if the backend response
 * contains additional fields later.
 */
export async function runBIOQUREAnalysis(datasetId, options = {}) {
  const result = await analyzePublicDataset(datasetId, options);

  return {
    ...result,
    datasetId:
      result?.dataset_id ??
      result?.datasetId ??
      datasetId,
  };
}

/**
 * Download a dataset using the browser.
 *
 * This helper creates a temporary browser download link.
 */
export async function savePublicDataset(datasetId, filename) {
  const response = await downloadPublicDataset(datasetId);

  const blob = await response.blob();

  let finalFilename = filename;

  if (!finalFilename) {
    const disposition = response.headers.get("content-disposition") || "";

    const match = disposition.match(
      /filename\*?=(?:UTF-8'')?["']?([^;"']+)["']?/i
    );

    finalFilename = match?.[1]
      ? decodeURIComponent(match[1])
      : `${datasetId}.tsv`;
  }

  const url = window.URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = finalFilename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.URL.revokeObjectURL(url);
}

/* =========================================================
   LEGACY DATASET API
   =========================================================
   These are retained temporarily so the rest of the existing
   frontend does not immediately break while we migrate the
   old GeneZap DatasetPoolPanel to BIOQURE.
   ========================================================= */

export async function listPools() {
  return request("/../datasets/pools", {
    method: "GET",
  });
}

export async function getDefaultPool() {
  return request("/../datasets/pools/default", {
    method: "GET",
  });
}

export async function createPool(payload) {
  return request("/../datasets/pools", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getPool(poolId) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  return request(`/../datasets/pools/${encodeURIComponent(poolId)}`, {
    method: "GET",
  });
}

export async function deletePool(poolId) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  return request(`/../datasets/pools/${encodeURIComponent(poolId)}`, {
    method: "DELETE",
  });
}

export async function uploadPoolFiles(poolId, formData) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  if (!(formData instanceof FormData)) {
    throw new Error("uploadPoolFiles requires FormData.");
  }

  const response = await fetch(
    `${API_BASE}/datasets/pools/${encodeURIComponent(poolId)}/files`,
    {
      method: "POST",
      body: formData,
    }
  );

  return parseResponse(response);
}

export async function importPoolFromPath(poolId, payload) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  return request(
    `/../datasets/pools/${encodeURIComponent(poolId)}/import`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function snapshotPool(poolId, payload = {}) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  return request(
    `/../datasets/pools/${encodeURIComponent(poolId)}/snapshot`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function analyzePoolFile(poolId, filename, payload = {}) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  if (!filename) {
    throw new Error("Filename is required.");
  }

  return request(
    `/../datasets/pools/${encodeURIComponent(poolId)}/files/${encodeURIComponent(
      filename
    )}/analyze`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function startBatchJob(poolId, payload = {}) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  return request(
    `/../datasets/pools/${encodeURIComponent(poolId)}/batch`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function getBatchJobStatus(poolId, jobId) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  return request(
    `/../datasets/pools/${encodeURIComponent(poolId)}/batch/${encodeURIComponent(
      jobId
    )}`,
    {
      method: "GET",
    }
  );
}

export async function getBatchJobResult(poolId, jobId) {
  if (!poolId) {
    throw new Error("Pool ID is required.");
  }

  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  return request(
    `/../datasets/pools/${encodeURIComponent(poolId)}/batch/${encodeURIComponent(
      jobId
    )}/result`,
    {
      method: "GET",
    }
  );
}

/* =========================================================
   ERROR HELPER
   ========================================================= */

export function readApiErrorDetail(error) {
  if (!error) {
    return "Unknown error.";
  }

  if (typeof error === "string") {
    return error;
  }

  if (error.message) {
    return error.message;
  }

  if (error.detail) {
    return typeof error.detail === "string"
      ? error.detail
      : JSON.stringify(error.detail);
  }

  return "Request failed.";
}

export async function uploadDataset(file, onProgress) {
  if (!file) throw new Error("Choose a STAR-counts TSV file.");
  if (!file.name.endsWith(".rna_seq.augmented_star_gene_counts.tsv")) {
    throw new Error("File must end with .rna_seq.augmented_star_gene_counts.tsv.");
  }
  const formData = new FormData();
  formData.append("file", file);
  onProgress?.(0);
  const result = await request("/predict/upload", { method: "POST", body: formData });
  onProgress?.(100);
  return result;
}