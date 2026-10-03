/**
 * Built-in fallback for the product tour.
 *
 * The live tour is loaded at runtime from `public/tour-steps.json`
 * (or from VITE_TOUR_CONFIG_URL, e.g. an admin API). Edit that file to add,
 * remove, reorder or disable steps – no component code needs to change.
 * This copy is only used if the JSON cannot be loaded.
 *
 * Step fields:
 *   id         unique key
 *   target     CSS selector, or an array of selectors tried in order
 *              (first visible match is highlighted; none = centered card)
 *   title      step heading
 *   body       short explanation
 *   placement  "auto" | "top" | "bottom" | "left" | "right"
 *   enabled    set false to hide a step without deleting it
 *
 * Bump `version` to show the tour again to every returning visitor
 * (e.g. after shipping new features).
 */
export const DEFAULT_TOUR = {
  version: "1.0.0",
  autoStart: true,
  welcomeDelayMs: 900,
  documentationUrl: "/docs",
  supportUrl: "mailto:support@bioqure.ai",
  statusEndpoint: "",
  welcome: {
    eyebrow: "WELCOME TO BIOQURE",
    title: "Your breast-cancer research workspace",
    body: "BIOQURE lets you pick a curated public expression dataset, run it through a shared preprocessing pipeline, and compare classical and quantum machine-learning inference – all in one place.",
    highlights: [
      "Curated TCGA / GDC datasets",
      "Classical + Qiskit VQC models",
      "Benchmark, biomarker and quantum reports",
    ],
    primaryLabel: "Take a Quick Guide",
    secondaryLabel: "Skip for Now",
  },
  completion: {
    title: "You're all set!",
    body: "You now know how to run a test from start to finish.",
    primaryLabel: "Start My First Test",
    primaryTarget: ["[data-tour='dataset-card']", "[data-tour='dataset-search']", "#datasets"],
    secondaryLabel: "View Documentation",
  },
  steps: [
    {
      id: "dashboard",
      target: ["[data-tour='dashboard']", "#overview"],
      title: "Your research dashboard",
      body: "This is mission control. It summarises the platform – dataset pool, models, qubits and shots – and shows the four-step workflow you'll follow for every analysis.",
      placement: "auto",
    },
    {
      id: "dataset-pool",
      target: ["[data-tour='dataset-collection']", "#datasets"],
      title: "Choose what to test",
      body: "The dataset pool lists every curated public breast-cancer expression dataset available to BIOQURE, grouped by source and data type.",
      placement: "auto",
    },
    {
      id: "dataset-card",
      target: ["[data-tour='dataset-card']", "[data-tour='dataset-collection']"],
      title: "Pick a specific dataset",
      body: "Click any dataset card to select it. Its ID, access level, sample count and gene count are shown so you can choose the right cohort.",
      placement: "auto",
    },
    {
      id: "configuration",
      target: ["[data-tour='dataset-filters']", "[data-tour='dataset-workspace']"],
      title: "Search & configure",
      body: "Filter the pool by dataset ID, project, source or description, and refresh it at any time. After selecting, review the metadata (or raw JSON) in the workspace before you start.",
      placement: "auto",
    },
    {
      id: "start",
      target: ["[data-tour='run-analysis']", "[data-tour='dataset-workspace']"],
      title: "Launch the analysis",
      body: "Press “Run BIOQURE Analysis” to send the selected dataset through preprocessing, gene-funnel feature selection and model inference.",
      placement: "auto",
    },
    {
      id: "progress",
      target: ["[data-tour='analysis-result']", "[data-tour='dataset-workspace']"],
      title: "Follow the run",
      body: "While the job runs the button switches to “Running BIOQURE…”. When it finishes, the prediction, confidence and model summary appear right here in the workspace.",
      placement: "auto",
    },
    {
      id: "results",
      target: ["[data-tour='report']", "#report"],
      title: "Read your research report",
      body: "The full report opens below with the prediction, selected model and confidence, plus a model overview you can interpret at a glance.",
      placement: "auto",
    },
    {
      id: "export",
      target: ["[data-tour='report-tabs']", "[data-tour='download-dataset']", "#report"],
      title: "Explore, save & share",
      body: "Switch between Overview, Benchmark, Quantum, Biomarkers and Input metrics, and use “Download Dataset” to save the exact data you analysed for sharing or offline review.",
      placement: "auto",
    },
  ],
};
