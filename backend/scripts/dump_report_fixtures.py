"""Write locked inference responses for public demo samples as JSON fixtures.

Used by frontend/scripts/report-render-check.mjs to render the report tabs
against real backend output. Usage: python backend/scripts/dump_report_fixtures.py <dir>
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inference_service.inference import ROOT, LockedInferenceEngine  # noqa: E402

DEMO_IDS = ("BRCA-DEMO-001", "BRCA-DEMO-009")


def main(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    engine = LockedInferenceEngine()
    for demo_id in DEMO_IDS:
        item = engine.demo_samples[demo_id]
        result = engine.infer((ROOT / item["fixture_path"]).read_bytes(), "demo", item["display_name"], item.get("sample_type"))
        (output_dir / f"{demo_id}.json").write_text(json.dumps(result), encoding="utf-8")
        print(f"{demo_id}: {result['predictions']['classical_logistic']['predicted_class']}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "report_fixtures"))
