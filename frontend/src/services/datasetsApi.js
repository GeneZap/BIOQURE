import { API_BASE } from "../config.js";

const BASE = `${API_BASE}/api/v1`;

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message =
      typeof payload === "string" && payload.trim()
        ? payload
        : payload?.detail || payload?.message || "Request failed.";
    const error = new Error(
      typeof message === "string" ? message : JSON.stringify(message),
    );
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

export async function getPublicDataset(datasetId) {
  if (!datasetId) throw new Error("Dataset ID is required.");
  const response = await listPublicDatasets();
  const dataset = response.datasets.find((item) => item.dataset_id === datasetId);
  if (!dataset) throw new Error("Public sample was not found.");
  return dataset;
}

export async function analyzePublicDataset(datasetId, options = {}) {
  if (!datasetId) throw new Error("Dataset ID is required.");
  return request(`/predict/demo/${encodeURIComponent(datasetId)}`, {
    method: "POST",
    body: JSON.stringify(options),
  });
}

export async function getBIOQUREStatus() {
  return request("/health", { method: "GET" });
}

/**
 * Downloads the underlying dataset file to the user's computer.
 *
 * NOTE: the exact backend route below ("/demo-samples/{id}/download") is a
 * best guess based on the "/demo-samples" listing endpoint — this project's
 * FastAPI backend code wasn't available to confirm the real route name.
 * If this 404s in the browser console, check the backend's route
 * definitions (likely in a file like routers/demo_samples.py or similar)
 * for the actual download endpoint and update the path below to match.
 */
export async function savePublicDataset(datasetId, fileName) {
  if (!datasetId) throw new Error("Dataset ID is required.");

  const response = await fetch(
    `${BASE}/demo-samples/${encodeURIComponent(datasetId)}/download`,
  );

  if (!response.ok) {
    throw new Error(
      `Dataset download failed (status ${response.status}). Check the backend route for downloading demo sample files.`,
    );
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName || `${datasetId}.tsv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function uploadDataset(file, onProgress) {
  if (!file) throw new Error("Choose a STAR-counts TSV file.");
  if (!file.name.endsWith(".rna_seq.augmented_star_gene_counts.tsv")) {
    throw new Error("File must end with .rna_seq.augmented_star_gene_counts.tsv.");
  }
  const formData = new FormData();
  formData.append("file", file);
  onProgress?.(0);
  const result = await request("/predict/upload", {
    method: "POST",
    body: formData,
  });
  onProgress?.(100);
  return result;
}