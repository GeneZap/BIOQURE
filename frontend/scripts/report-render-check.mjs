// Renders every report tab against real locked-backend responses and fails if
// expected values are missing. Generate the responses first with:
//   python backend/scripts/dump_report_fixtures.py <dir>
// then run: REPORT_FIXTURE_DIR=<dir> npm run check:reports
import { readFileSync } from "node:fs";
import { join } from "node:path";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const fixtureDir = process.env.REPORT_FIXTURE_DIR || "/tmp";
const expected = {
  ReportMetrics: ["Logistic regression", "Selected model", "Selected "],
  ReportBenchmark: ["Candidate A", "95.9%", "Not evaluated", "Selected"],
  ReportQuantum: ["ZZFeatureMap", "2,048"],
  ReportBiomarkers: ["FABP4", "LEP", "COL10A1", "CHRDL1", "SCARA5", "SAA1", "SFRP1", "LPL"],
  ReportInputMetrics: ["60,660", "COL10A1"],
};

// Text that must never appear: unevaluated checks shown as failed, missing logistic metrics shown as 0.
const forbidden = {
  ReportBenchmark: ["Not passed", "Not demonstrated", "0.0%", "0.000"],
  ReportMetrics: ["0.0% AUC", "Accuracy 0.0%"],
};

const server = await createServer({ server: { middlewareMode: true }, appType: "custom", logLevel: "error" });
let failed = false;
try {
  for (const demo of ["BRCA-DEMO-001", "BRCA-DEMO-009"]) {
    const analysis = JSON.parse(readFileSync(join(fixtureDir, `${demo}.json`), "utf8"));
    for (const [name, needles] of Object.entries(expected)) {
      const Component = (await server.ssrLoadModule(`/src/components/report/${name}.jsx`)).default;
      const props = name === "ReportBenchmark" ? { benchmark: analysis.benchmark, result: analysis } : { result: analysis };
      const text = renderToStaticMarkup(React.createElement(Component, props)).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
      if (process.env.DUMP === name) console.log(text);
      const missing = needles.filter((needle) => !text.includes(needle));
      for (const bad of forbidden[name] || []) if (text.includes(bad)) missing.push(`forbidden "${bad}"`);
      if (missing.length) failed = true;
      console.log(`${demo} ${name}: ${missing.length ? `MISSING ${missing.join(", ")}` : "ok"}`);
    }
  }
} finally {
  await server.close();
}
process.exit(failed ? 1 : 0);
