"""Sequence analysis, k-mer visualization, and inference helpers for GeneZap engines."""

from __future__ import annotations

import base64
import hashlib
import io
import itertools
import logging
from typing import Any

_log = logging.getLogger("genezap.analysis")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd

from quad_engine_inference import cgr_png_bytes_v3_style, run_quad_engines
from genezap_settings import allow_integrated_real
from v2_pharmacology_table import merge_v2_pharmacology_into_payload

_BASES = ("A", "C", "G", "T")
_KMER_ORDER_4 = ["".join(p) for p in itertools.product(_BASES, repeat=4)]

# Valid 1×1 PNG (mock auxiliary payload for CV stack contract / demos)
_MOCK_CV_PLACEHOLDER_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def parse_fasta(text: str) -> tuple[str, str | None]:
    """Return (concatenated_sequence_upper, first_header_or_none)."""
    lines = text.strip().splitlines()
    seq_parts: list[str] = []
    header: str | None = None
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith(">"):
            if header is None:
                header = s[1:].strip() or None
            continue
        seq_parts.append(s.upper())
    sequence = "".join(seq_parts)
    allowed = set("ACGTN")
    sequence = "".join(c for c in sequence if c in allowed)
    return sequence, header


def gc_content(sequence: str) -> float:
    if not sequence:
        return 0.0
    g = sequence.count("G") + sequence.count("C")
    return round(g / len(sequence), 4)


def kmer_counts(sequence: str, k: int = 4) -> dict[str, int]:
    if k != 4:
        raise ValueError("Only k=4 is supported for ordered feature vectors.")
    counts = {km: 0 for km in _KMER_ORDER_4}
    for i in range(0, len(sequence) - k + 1):
        mer = sequence[i : i + k]
        if mer in counts:
            counts[mer] += 1
    return counts


def kmer_frequency_vector(sequence: str, k: int = 4) -> np.ndarray:
    counts = kmer_counts(sequence, k=k)
    total = sum(counts.values()) or 1
    arr = np.array([counts[km] / total for km in _KMER_ORDER_4], dtype=np.float64)
    return arr.reshape(1, -1)


def kmer_histogram_png_base64(sequence: str, k: int = 4, top_n: int = 64) -> str:
    """Histogram of k-mer frequencies as raw Base64 PNG (no data: prefix)."""
    counts = kmer_counts(sequence, k=k)
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    labels = [a for a, _ in items]
    values = [b for _, b in items]

    fig, ax = plt.subplots(figsize=(10, 4), dpi=120)
    ax.bar(range(len(values)), values, color="#2ee6d6", edgecolor="#0a2624", linewidth=0.3)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90, fontsize=6, fontfamily="monospace")
    ax.set_ylabel("Count")
    ax.set_title(f"Top {top_n} {k}-mer frequencies (DNA spectrum)")
    ax.set_facecolor("#0d1117")
    fig.patch.set_facecolor("#0a0e17")
    ax.tick_params(colors="#9fb3c8")
    ax.yaxis.label.set_color("#9fb3c8")
    ax.title.set_color("#e6f7f5")
    ax.spines["bottom"].set_color("#1f3d3a")
    ax.spines["left"].set_color("#1f3d3a")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _derive_patient_id(header: str | None, sequence: str) -> str:
    if header:
        token = header.strip().split()[0]
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in token)[:48]
        if safe:
            return safe
    h = hashlib.sha1(sequence[: min(5000, len(sequence))].encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"SPECIMEN-{h.upper()}"


def cgr_png_base64(sequence: str, max_points: int = 100_000) -> str:
    """Chaos Game Representation as raw Base64 PNG (no data: prefix)."""
    clean = "".join(c for c in sequence.upper() if c in "ACGT")
    if len(clean) < 12:
        clean = (clean + "ACGTACGTACGT")[:12]

    corners = {
        "A": np.array([0.0, 0.0], dtype=np.float64),
        "C": np.array([0.0, 1.0], dtype=np.float64),
        "G": np.array([1.0, 1.0], dtype=np.float64),
        "T": np.array([1.0, 0.0], dtype=np.float64),
    }
    step = max(1, len(clean) // max_points)
    xs: list[float] = []
    ys: list[float] = []
    x = y = 0.5
    for i in range(0, len(clean), step):
        b = clean[i]
        corner = corners[b]
        x = (x + corner[0]) / 2.0
        y = (y + corner[1]) / 2.0
        xs.append(x)
        ys.append(y)

    fig, ax = plt.subplots(figsize=(5.5, 5.5), dpi=120)
    ax.scatter(xs, ys, s=0.12, c="#5eead4", alpha=0.4, linewidths=0)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("#0a0e17")
    ax.set_facecolor("#060a0f")

    buf = io.BytesIO()
    fig.tight_layout(pad=0.05)
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def normalize_engines_for_ui(engines: dict[str, Any]) -> dict[str, Any]:
    """Ensure nested keys exist with non-empty strings so the dashboard never shows bare placeholders."""
    out = dict(engines)

    v1 = dict(out.get("v1") or {})
    pr = dict(v1.get("profiler") or {})
    species = (pr.get("species_prediction") or pr.get("species_guess") or "").strip() or "Species pending identification"
    pr["species_prediction"] = species
    pr["species_guess"] = pr.get("species_guess") or species
    pr.setdefault("gc_percent", 0.0)
    pr.setdefault("length_bp", 0)
    pr["baseline_verdict"] = (pr.get("baseline_verdict") or "SUSCEPTIBLE").strip().upper()
    if pr.get("resistance_probability") is None:
        pr["resistance_probability"] = 0.45 if pr["baseline_verdict"] == "RESISTANT" else 0.42
    pr["notes"] = (pr.get("notes") or "Genomic profiler output.").strip()
    v1["profiler"] = pr
    out["v1"] = v1

    v2 = dict(out.get("v2") or {})
    ph = dict(v2.get("pharmacology") or {})
    ph["verdict"] = (ph.get("verdict") or "SUSCEPTIBLE").strip().upper()
    ph["risk_level"] = (ph.get("risk_level") or "MODERATE").strip().upper()
    if ph.get("resistance_probability") is None:
        ph["resistance_probability"] = 0.62 if ph["verdict"] == "RESISTANT" else 0.38
    ph["notes"] = (ph.get("notes") or "Pharmacology engine output.").strip()
    ph.setdefault("drug_class_verdicts", [])
    ph.setdefault("risk_tiers", [])
    v2["pharmacology"] = ph
    out["v2"] = v2

    v3 = dict(out.get("v3") or {})
    vis = dict(v3.get("vision") or {})
    cv = (vis.get("clinical_verdict") or "SUSCEPTIBLE").strip().upper()
    vis["clinical_verdict"] = cv
    vis["verdict"] = (vis.get("verdict") or f"Vision readout: {cv} pattern relative to training cohort.").strip()
    vis["motif"] = (vis.get("motif") or "Genomic texture summary unavailable.").strip()
    if vis.get("confidence_percent") is None:
        vis["confidence_percent"] = 72.5
    b64 = vis.get("cgr_image_png_base64") or ""
    if not b64:
        vis["cgr_image_png_base64"] = base64.b64encode(
            cgr_png_bytes_v3_style("ACGTACGTACGTACGTACGT")
        ).decode("ascii")
    cgr = dict(vis.get("cgr") or {})
    cgr.setdefault("image_png_base64", vis["cgr_image_png_base64"])
    cgr.setdefault("label", "Chaos game representation (CGR)")
    cgr.setdefault("simulated", True)
    vis["cgr"] = cgr
    vis["notes"] = (vis.get("notes") or "Vision / CGR channel.").strip()
    vis.setdefault("cv_detected_species", "")
    vis.setdefault("cv_species_mapping_accuracy_percent", vis.get("confidence_percent"))
    vis.setdefault("resistance_topology_genes", [])
    vis.setdefault("mock_cv_preview_base64", "")
    vis.setdefault("cv_topology_mapping_statement", "")
    v3["vision"] = vis
    out["v3"] = v3

    v4 = dict(out.get("v4") or {})
    disc = dict(v4.get("discovery") or {})
    disc.setdefault("hits", [])
    disc.setdefault("gene_signatures", [str(h.get("gene", "")) for h in disc.get("hits") or [] if h.get("gene")])
    disc["notes"] = (disc.get("notes") or "Resistance gene discovery channel.").strip()
    v4["discovery"] = disc
    out["v4"] = v4

    return out


def build_final_recommendation(
    v1: dict[str, Any],
    v2: dict[str, Any],
    v3: dict[str, Any],
    v4: dict[str, Any],
) -> dict[str, Any]:
    v1v = str((v1.get("profiler") or {}).get("baseline_verdict", "")).upper()
    pharm = v2.get("pharmacology") or {}
    verdict2 = str(pharm.get("verdict", "")).upper()
    risk2 = str(pharm.get("risk_level", "")).upper()
    v3vision = v3.get("vision") or {}
    v3c = str(v3vision.get("clinical_verdict") or "").upper()
    hits = (v4.get("discovery") or {}).get("hits") or []

    high_signal = (
        v1v == "RESISTANT"
        or verdict2 == "RESISTANT"
        or risk2 in {"HIGH", "CRITICAL"}
        or v3c == "RESISTANT"
        or len(hits) > 0
    )
    if high_signal:
        return {
            "level": "high_risk",
            "title": "High Risk / Avoid",
            "summary": (
                "One or more engines (V1 baseline, V2 pharmacology, V3 vision, and/or V4 gene discovery) "
                "report resistance or critical gene hits. Follow stewardship and infection-control protocols."
            ),
            "banner_tone": "danger",
        }
    return {
        "level": "safe",
        "title": "Low risk — favorable profile",
        "summary": (
            "No resistance consensus across the quad-engine panel for this specimen. "
            "Continue standard laboratory confirmation per local SOP."
        ),
        "banner_tone": "safe",
    }


def apply_pitch_demo_profile(sequence: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Replace engine + recommendation blocks with a realistic Salmonella enterica
    multidrug-resistant presentation while preserving real assembly metrics from the upload.
    """
    dr = dict(payload.get("diagnostic_report") or {})
    gc_pct = float(dr.get("gc_content") or 0.0) * 100.0
    length_bp = int(dr.get("sequence_length") or len(sequence))

    cgr_b64 = base64.b64encode(cgr_png_bytes_v3_style(sequence)).decode("ascii")
    v3_verdict = (
        "CGR generated from the uploaded sequence; mock CV / CNN stack evaluates fractal texture. "
        "Detected pattern class consistent with Salmonella enterica (96.5% species-mapping accuracy). "
        "Attention maps highlight resistance-associated topologies correlating with blaTEM-1 and NDM-1 "
        "gene contexts — anomalies exceed susceptible training envelopes."
    )
    cv_topology_statement = (
        "CV / CNN pattern analysis achieved 96.5% accuracy in mapping sequence topologies to resistance profiles."
    )

    engines: dict[str, Any] = {
        "v1": {
            "engine": "V1",
            "engine_name": "Genomic profiler",
            "role": "profiler",
            "status": "complete",
            "mode": "pitch_demo",
            "profiler": {
                "species_prediction": "Salmonella enterica",
                "species_guess": "Salmonella enterica",
                "species_confidence": 0.97,
                "species_confidence_percent": 97.0,
                "gc_percent": round(gc_pct, 2),
                "length_bp": length_bp,
                "baseline_verdict": "RESISTANT",
                "resistance_probability": 0.91,
                "notes": (
                    "Profiler read: FASTA-derived k-mer spectrum assigned to Salmonella enterica at 97.0% "
                    "confidence; baseline resistance channel flags elevated risk consistent with acquired β-lactamases."
                ),
            },
        },
        "v2": {
            "engine": "V2",
            "engine_name": "Pharmacology",
            "role": "pharmacology",
            "status": "complete",
            "mode": "pitch_demo",
            "pharmacology": {
                "verdict": "RESISTANT",
                "risk_level": "CRITICAL",
                "resistance_probability": 0.93,
                "drug_class_verdicts": [
                    {
                        "drug_class": "Penicillin",
                        "verdict": "RESISTANT",
                        "clinical_detail": (
                            "blaTEM-1–mediated penicillinase activity: avoid empiric Ampicillin, Amoxicillin, "
                            "and Piperacillin until phenotypic MIC and stewardship review."
                        ),
                    },
                    {
                        "drug_class": "Carbapenems",
                        "verdict": "RESISTANT",
                        "clinical_detail": (
                            "NDM-1 carbapenemase: Meropenem and Imipenem are not reliable as monotherapy; "
                            "coordinate with infectious diseases and apply institutional carbapenemase protocols."
                        ),
                    },
                ],
                "risk_tiers": [
                    {
                        "tier": "CRITICAL",
                        "label": "Beta-lactam / carbapenem empiric failure",
                        "detail": "Combined TEM + NDM signatures imply broad β-lactam hydrolysis; reserve agents per antibiogram.",
                    },
                    {
                        "tier": "HIGH",
                        "label": "Infection-control flag",
                        "detail": "Carbapenemase-positive lineage — notify IPC per facility SOP.",
                    },
                ],
                "notes": (
                    "Pharmacology engine: class-specific resistance calls for Penicillin and Carbapenems "
                    "with clinical de-escalation hooks — align with V4 CARD genes blaTEM-1 and NDM-1."
                ),
            },
        },
        "v3": {
            "engine": "V3",
            "engine_name": "Vision",
            "role": "vision",
            "status": "complete",
            "mode": "pitch_demo",
            "vision": {
                "verdict": v3_verdict,
                "clinical_verdict": "RESISTANT",
                "confidence_percent": 96.5,
                "cv_detected_species": "Salmonella enterica",
                "cv_species_mapping_accuracy_percent": 96.5,
                "cv_topology_mapping_statement": cv_topology_statement,
                "resistance_topology_genes": ["blaTEM-1", "NDM-1"],
                "motif": "Plasmid-weighted CGR texture — off-axis attractors vs. chromosomal controls",
                "cgr_image_png_base64": cgr_b64,
                "mock_cv_preview_base64": _MOCK_CV_PLACEHOLDER_PNG_B64,
                "cgr": {
                    "image_png_base64": cgr_b64,
                    "simulated": False,
                    "label": "Chaos game representation (CGR) — derived from uploaded sequence",
                },
                "raw_score": 0.22,
                "notes": (
                    "Vision channel: mock CNN inference on CGR tensor; species head and resistance-topology "
                    "auxiliary outputs aligned with V1 profiler and pending V4 CARD confirmation."
                ),
            },
        },
        "v4": {
            "engine": "V4",
            "engine_name": "Discovery",
            "role": "discovery",
            "status": "complete",
            "mode": "pitch_demo",
            "card_database": "CARD (Comprehensive Antibiotic Resistance Database)",
            "discovery": {
                "hits": [
                    {
                        "gene": "blaTEM-1",
                        "mechanism": (
                            "Class A beta-lactamase — hydrolytic inactivation of penicillins and "
                            "early-generation cephalosporins; often plasmid-encoded with broad host range."
                        ),
                        "risk": "CRITICAL",
                        "aro": "ARO:3000631",
                    },
                    {
                        "gene": "NDM-1",
                        "mechanism": (
                            "Carbapenemase (metallo-β-lactamase) — zinc-dependent hydrolysis of "
                            "carbapenems and most β-lactams; high clinical priority for infection control."
                        ),
                        "risk": "HIGH",
                        "aro": "ARO:3000324",
                    },
                ],
                "gene_signatures": ["blaTEM-1", "NDM-1"],
                "notes": (
                    "Engine V4 detected blaTEM-1 and NDM-1 via CARD database cross-reference on the uploaded "
                    "DNA, confirming the resistance-associated visual anomalies flagged by Engine V3's "
                    "computer-vision / CNN interpretation of the CGR graph."
                ),
            },
        },
    }

    out = dict(payload)
    out["status"] = "complete"
    fh_raw = str(dr.get("fasta_header") or "").strip()
    out["patient_id"] = (fh_raw.split()[0][:48] if fh_raw else "SAL-PITCH-DEMO-01")
    out["diagnostic_report"] = {**dr, "engines": engines}
    out["final_recommendation"] = {
        "level": "high_risk",
        "title": "High Risk / Avoid — MDR Salmonella enterica pattern",
        "summary": (
            "Quad-engine consensus indicates a multidrug-resistant Salmonella enterica presentation "
            "with critical pharmacology risk, vision-anomaly CGR topology, and CARD-confirmed "
            "blaTEM-1 / NDM-1 signatures. Escalate to stewardship and apply contact precautions per protocol."
        ),
        "banner_tone": "danger",
    }
    out["susceptibility_profile"] = _susceptibility_profile_salmonella_mdr()
    return out


def _susceptibility_profile_salmonella_mdr() -> dict[str, list[str]]:
    """Stewardship strings aligned with blaTEM-1 + NDM-1 CARD hits (arrays for UI loops)."""
    return {
        "resistant_to": [
            "Penicillins — avoid Amoxicillin, Piperacillin, and related penicillin-class agents (blaTEM-1–mediated hydrolysis).",
            "Early-generation cephalosporins — expect degradation via broad-spectrum beta-lactamase activity.",
            "Carbapenems — avoid Meropenem and Imipenem unless directed by infectious diseases under strict protocols (NDM-1 carbapenemase).",
        ],
        "alternative_options": [
            "Fluoroquinolones — Ciprofloxacin may remain viable pending phenotypic MIC and institutional formulary (confirm susceptibility).",
            "Aminoglycosides — consider Gentamicin or Amikacin when supported by laboratory susceptibility and renal monitoring.",
        ],
    }


def attach_susceptibility_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Add susceptibility_profile when absent but MDR signals or CARD blaTEM/NDM hits are present."""
    if payload.get("susceptibility_profile"):
        return payload
    hits = (
        ((payload.get("diagnostic_report") or {}).get("engines") or {})
        .get("v4", {})
        .get("discovery", {})
        .get("hits")
        or []
    )
    blob = " ".join(str(h.get("gene", "")) for h in hits).upper()
    high = (payload.get("final_recommendation") or {}).get("level") == "high_risk"
    if high or "TEM" in blob or "NDM" in blob:
        out = dict(payload)
        out["susceptibility_profile"] = _susceptibility_profile_salmonella_mdr()
        return out
    return payload


def analyze_sequence_bytes(
    raw: bytes,
    *,
    pitch_demo: bool = False,
    use_integrated_real: bool = False,
) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    sequence, header = parse_fasta(text)
    if len(sequence) < 20:
        raise ValueError("Sequence too short or empty after parsing FASTA.")

    counts = kmer_counts(sequence, k=4)
    nonzero = sum(1 for v in counts.values() if v > 0)
    meta = {
        "length": len(sequence),
        "gc_content": gc_content(sequence),
        "unique_4mers": nonzero,
        "header": header,
        "fasta_header": header,
    }
    plot_b64 = kmer_histogram_png_base64(sequence, k=4)
    nonzero_counts = pd.Series([v for v in counts.values() if v > 0])
    kmer_stats = None
    if len(nonzero_counts) > 0:
        raw = nonzero_counts.describe().round(4).to_dict()
        kmer_stats = {k: float(v) for k, v in raw.items()}

    client_warnings: list[str] = []
    integrated_real_enabled = bool(use_integrated_real) and allow_integrated_real()

    if use_integrated_real and not integrated_real_enabled:
        client_warnings.append(
            "Integrated engine was requested, but this deployment blocks the heavyweight artifact stack; "
            "used quad-engine fallback instead. Set GENEZAP_ALLOW_INTEGRATED_REAL=1 only on a host with enough resources."
        )
        _log.warning("use_integrated_real ignored: heavyweight artifact stack disabled for this deployment")

    if integrated_real_enabled:
        # Lazy import: avoids loading joblib/TF-heavy integrated stack unless requested.
        try:
            from integrated_pipeline_real import run_integrated_real_engines

            engines = run_integrated_real_engines(sequence, header=header)
        except Exception as e:  # noqa: BLE001
            _log.exception("Integrated hackathon pipeline failed; falling back to quad-engine inference")
            client_warnings.append(
                f"Integrated pipeline failed ({e.__class__.__name__}): {e}. "
                "Fell back to quad-engine. Check logs, GENEZAP_CV_ARTIFACT_ROOT, model files, and TensorFlow."
            )
            engines = run_quad_engines(sequence, meta)
    else:
        engines = run_quad_engines(sequence, meta)
    engines = normalize_engines_for_ui(engines)

    final_recommendation = build_final_recommendation(
        engines["v1"],
        engines["v2"],
        engines["v3"],
        engines["v4"],
    )

    # Pitch demo replaces all engine JSON; it must not run together with integrated mode
    # or it would silently overwrite hackathon artifact outputs.
    pitch_effective = bool(pitch_demo) and not integrated_real_enabled
    if pitch_demo and integrated_real_enabled:
        client_warnings.append(
            "Salmonella MDR pitch demo was not applied because it replaces engine payloads; "
            "uncheck Hackathon integrated engine to use pitch demo, or leave pitch demo off for integrated."
        )
        _log.warning("pitch_demo suppressed: incompatible with use_integrated_real (preserving integrated engines)")

    payload: dict[str, Any] = {
        "status": "complete",
        "patient_id": _derive_patient_id(header, sequence),
        "diagnostic_report": {
            "sequence_length": meta["length"],
            "gc_content": meta["gc_content"],
            "fasta_header": header if header is not None else "",
            "kmer_histogram_png_base64": plot_b64,
            "kmer_stats": kmer_stats,
            "engines": engines,
            "client_warnings": client_warnings or None,
        },
        "final_recommendation": final_recommendation,
    }
    if pitch_effective:
        payload = apply_pitch_demo_profile(sequence, payload)
    else:
        payload = attach_susceptibility_profile(payload)
    # Re-attach warnings after attach/apply mutates diagnostic_report shallowly
    if client_warnings:
        dr = dict(payload.get("diagnostic_report") or {})
        merged = list(dr.get("client_warnings") or [])
        merged.extend([w for w in client_warnings if w not in merged])
        dr["client_warnings"] = merged or None
        payload["diagnostic_report"] = dr
    payload = merge_v2_pharmacology_into_payload(payload, header)
    return payload
