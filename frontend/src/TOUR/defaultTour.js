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
  version: "1.1.0",
  autoStart: true,
  welcomeDelayMs: 900,
  documentationUrl: "/docs",
  supportUrl: "mailto:support@bioqure.ai",
  statusEndpoint: "",
  welcome: {
    eyebrow: "WELCOME TO BIOQURE",
    title: "Let's run your first test",
    body: "Pick a dataset, run it, and read the result — four short steps. This takes about a minute.",
    highlights: [
      "Pick a public dataset",
      "Run classical + quantum models",
      "Read the report",
    ],
    primaryLabel: "Show Me How",
    secondaryLabel: "Skip for Now",
  },
  completion: {
    title: "You're ready",
    body: "Pick any dataset below to run your first test.",
    primaryLabel: "Pick a Dataset",
    primaryTarget: ["[data-tour='dataset-card']", "[data-tour='dataset-search']", "#datasets"],
    secondaryLabel: "View Documentation",
  },
  steps: [
    {
      id: "dashboard",
      target: ["[data-tour='dashboard']", "#overview"],
      title: "1. Your workspace",
      body: "This is where every test starts and finishes — pick a dataset below, then read the result up here.",
      placement: "auto",
    },
    {
      id: "dataset-pool",
      target: ["[data-tour='dataset-collection']", "#datasets"],
      title: "2. Pick a dataset",
      body: "These are real public breast-cancer datasets. Click one to select it.",
      placement: "auto",
    },
    {
      id: "start",
      target: ["[data-tour='run-analysis']", "[data-tour='dataset-workspace']"],
      title: "3. Run it",
      body: "Press \"Run BIOQURE Analysis\" to start. It checks the data with both classical and quantum models.",
      placement: "auto",
    },
    {
      id: "results",
      target: ["[data-tour='report']", "#report"],
      title: "4. Read the result",
      body: "Your prediction and confidence appear here. Open \"How to read this report\" if any term is unfamiliar.",
      placement: "auto",
    },
    {
      id: "export",
      target: ["[data-tour='report-tabs']", "[data-tour='download-dataset']", "#report"],
      title: "Want more detail?",
      body: "The tabs above break the result down further — model comparison, quantum details, and the genes involved.",
      placement: "auto",
    },
  ],
};
