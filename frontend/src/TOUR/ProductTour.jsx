import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowLeft, ArrowRight, BookOpen, Check, Compass, Rocket, X } from "lucide-react";
import { DEFAULT_TOUR } from "./defaultTour.js";
import { TOUR_EVENTS } from "./tourEvents.js";
import "./tour.css";

const STORAGE_KEY = "bioqure.productTour";
const CONFIG_URL = import.meta.env.VITE_TOUR_CONFIG_URL || `${import.meta.env.BASE_URL}tour-steps.json`;
const PAD = 8;
const GAP = 16;
const MARGIN = 12;
const MOBILE_BP = 640;

/* ---------------- config + persistence ---------------- */

function normalizeConfig(raw) {
  const base = DEFAULT_TOUR;
  const cfg = raw && typeof raw === "object" ? raw : {};
  const pickSteps = (list) =>
    (Array.isArray(list) ? list : []).filter((s) => s && s.title && s.enabled !== false);
  const steps = pickSteps(cfg.steps);
  return {
    ...base,
    ...cfg,
    welcome: { ...base.welcome, ...cfg.welcome },
    completion: { ...base.completion, ...cfg.completion },
    steps: steps.length ? steps : pickSteps(base.steps),
  };
}

function readStatus() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
  } catch {
    return null;
  }
}

function saveStatus(status, config) {
  const record = { status, version: config.version, at: new Date().toISOString() };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
  } catch {
    /* storage unavailable (private mode) – tour simply shows again */
  }
  if (config.statusEndpoint) {
    fetch(config.statusEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(record),
    }).catch(() => {});
  }
}

/* ---------------- DOM helpers ---------------- */

function findTarget(selectors) {
  for (const sel of [].concat(selectors || [])) {
    let nodes = [];
    try {
      nodes = document.querySelectorAll(sel);
    } catch {
      continue;
    }
    for (const el of nodes) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden") return el;
    }
  }
  return null;
}

function headerOffset() {
  const header = document.querySelector("header");
  return header && getComputedStyle(header).position === "sticky" ? header.offsetHeight : 0;
}

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

function ensureVisible(el) {
  const r = el.getBoundingClientRect();
  const top = headerOffset() + MARGIN;
  const mobile = window.innerWidth < MOBILE_BP;
  const bottom = mobile ? window.innerHeight * 0.52 : window.innerHeight - MARGIN;
  if (r.top >= top && r.bottom <= bottom) return;
  const avail = bottom - top;
  const delta = r.height + PAD * 2 > avail ? r.top - top - PAD : r.top - top - (avail - r.height) / 2;
  window.scrollTo({
    top: Math.max(0, window.scrollY + delta),
    behavior: prefersReducedMotion() ? "auto" : "smooth",
  });
}

function sameRect(a, b) {
  if (!a || !b) return a === b;
  return a.top === b.top && a.left === b.left && a.width === b.width && a.height === b.height;
}

function computeCardPosition(rect, card, vp, placement) {
  const clampX = (x) => Math.min(Math.max(x, MARGIN), vp.w - card.w - MARGIN);
  const minY = headerOffset() + MARGIN;
  const clampY = (y) => Math.min(Math.max(y, minY), vp.h - card.h - MARGIN);
  if (!rect) return { top: (vp.h - card.h) / 2, left: (vp.w - card.w) / 2, side: "center" };

  const hl = {
    top: rect.top - PAD,
    left: rect.left - PAD,
    right: rect.left + rect.width + PAD,
    bottom: rect.top + rect.height + PAD,
  };
  const cx = rect.left + rect.width / 2;
  const cy = Math.min(Math.max(rect.top + rect.height / 2, minY + card.h / 2), vp.h - card.h / 2);
  const options = {
    bottom: { top: hl.bottom + GAP, left: clampX(cx - card.w / 2), ok: hl.bottom + GAP + card.h <= vp.h - MARGIN },
    top: { top: hl.top - GAP - card.h, left: clampX(cx - card.w / 2), ok: hl.top - GAP - card.h >= minY },
    right: { top: clampY(cy - card.h / 2), left: hl.right + GAP, ok: hl.right + GAP + card.w <= vp.w - MARGIN },
    left: { top: clampY(cy - card.h / 2), left: hl.left - GAP - card.w, ok: hl.left - GAP - card.w >= MARGIN },
  };
  const order = [placement, "right", "left", "bottom", "top"].filter((p, i, a) => options[p] && a.indexOf(p) === i);
  for (const side of order) {
    if (options[side].ok) return { top: options[side].top, left: options[side].left, side };
  }
  // Target fills the screen: float the card in the lower-right corner over it.
  return { top: vp.h - card.h - MARGIN * 2, left: vp.w - card.w - MARGIN * 2, side: "inside" };
}

/* ---------------- component ---------------- */

export default function ProductTour() {
  const [config, setConfig] = useState(() => normalizeConfig(null));
  const [mode, setMode] = useState("idle"); // idle | welcome | tour | done
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState(null);
  const [viewport, setViewport] = useState({ w: window.innerWidth, h: window.innerHeight });
  const [cardSize, setCardSize] = useState({ w: 380, h: 240 });
  const cardRef = useRef(null);
  const primaryRef = useRef(null);
  const configRef = useRef(config);

  useEffect(() => {
    configRef.current = config;
  }, [config]);

  const steps = config.steps;
  const step = steps[Math.min(index, steps.length - 1)];
  const mobile = viewport.w < MOBILE_BP;

  // Load the admin-editable tour definition and auto-open for first-time visitors.
  useEffect(() => {
    let timer;
    let cancelled = false;
    fetch(CONFIG_URL, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null)
      .then((raw) => {
        if (cancelled) return;
        const cfg = normalizeConfig(raw);
        setConfig(cfg);
        const status = readStatus();
        if (cfg.autoStart !== false && (!status || status.version !== cfg.version)) {
          timer = setTimeout(() => setMode((m) => (m === "idle" ? "welcome" : m)), cfg.welcomeDelayMs ?? 900);
        }
      });
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  const startTour = useCallback(() => {
    setIndex(0);
    setRect(null);
    setMode("tour");
  }, []);

  // Global triggers (Help menu, "Take Product Tour" buttons, …)
  useEffect(() => {
    const openUrl = (url) => url && window.open(url, url.startsWith("mailto:") ? "_self" : "_blank", "noopener");
    const handlers = {
      [TOUR_EVENTS.start]: startTour,
      [TOUR_EVENTS.welcome]: () => setMode("welcome"),
      [TOUR_EVENTS.docs]: () => openUrl(configRef.current.documentationUrl),
      [TOUR_EVENTS.support]: () => openUrl(configRef.current.supportUrl),
    };
    Object.entries(handlers).forEach(([name, fn]) => window.addEventListener(name, fn));
    return () => Object.entries(handlers).forEach(([name, fn]) => window.removeEventListener(name, fn));
  }, [startTour]);

  // Track the highlighted element every frame so the spotlight follows scrolling,
  // resizing, and content that loads in late (e.g. datasets from the API).
  useEffect(() => {
    if (mode !== "tour" || !step) return undefined;
    let el = findTarget(step.target);
    if (el) ensureVisible(el);
    else window.scrollTo({ top: window.scrollY });
    let frame = 0;
    let raf = 0;
    const tick = () => {
      frame += 1;
      if ((!el || !el.isConnected) && frame % 20 === 0) {
        el = findTarget(step.target);
        if (el) ensureVisible(el);
      }
      let next = null;
      if (el?.isConnected) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          next = { top: Math.round(r.top), left: Math.round(r.left), width: Math.round(r.width), height: Math.round(r.height) };
        }
      }
      setRect((prev) => (sameRect(prev, next) ? prev : next));
      setViewport((v) => (v.w === window.innerWidth && v.h === window.innerHeight ? v : { w: window.innerWidth, h: window.innerHeight }));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [mode, step]);

  useLayoutEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const next = { w: el.offsetWidth, h: el.offsetHeight };
    setCardSize((prev) => (prev.w === next.w && prev.h === next.h ? prev : next));
  }, [mode, index, viewport.w]);

  useEffect(() => {
    if (mode !== "idle") primaryRef.current?.focus({ preventScroll: true });
  }, [mode, index]);

  const finishTour = useCallback(() => {
    saveStatus("completed", configRef.current);
    setMode("done");
  }, []);

  const skip = useCallback(() => {
    saveStatus("skipped", configRef.current);
    setMode("idle");
  }, []);

  const next = useCallback(() => {
    if (index >= steps.length - 1) finishTour();
    else setIndex((i) => i + 1);
  }, [index, steps.length, finishTour]);

  const prev = useCallback(() => setIndex((i) => Math.max(0, i - 1)), []);

  useEffect(() => {
    if (mode === "idle") return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") skip();
      if (mode !== "tour") return;
      if (e.key === "ArrowRight") next();
      if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, next, prev, skip]);

  function startFirstTest() {
    setMode("idle");
    const el = findTarget(config.completion.primaryTarget);
    if (!el) return;
    ensureVisible(el);
    el.classList.add("bq-tour-pulse");
    setTimeout(() => el.classList.remove("bq-tour-pulse"), 2400);
    if (typeof el.focus === "function") el.focus({ preventScroll: true });
  }

  if (mode === "idle") return null;

  const { welcome, completion } = config;
  let content = null;

  if (mode === "welcome") {
    content = (
      <div className="bq-tour-modal-wrap" role="dialog" aria-modal="true" aria-labelledby="bq-tour-welcome-title">
        <div className="bq-tour-backdrop" onClick={skip} />
        <div className="bq-tour-modal bq-hud bq-tour-pop">
          <button type="button" className="bq-tour-close" aria-label="Close" onClick={skip}>
            <X className="size-4" aria-hidden />
          </button>
          <div className="bq-tour-orbit" aria-hidden>
            <Compass className="size-6" />
          </div>
          <div className="bq-callout-tag mt-5 inline-block">{welcome.eyebrow}</div>
          <h2 id="bq-tour-welcome-title" className="bq-display mt-3 text-2xl font-semibold uppercase tracking-[0.04em] text-[var(--bq-text)] sm:text-[28px]">
            {welcome.title}
          </h2>
          <p className="mt-3 text-sm leading-6 text-[var(--bq-text-dim)]">{welcome.body}</p>
          {welcome.highlights?.length > 0 && (
            <ul className="mt-4 space-y-2">
              {welcome.highlights.map((h) => (
                <li key={h} className="flex items-center gap-2.5 text-[13px] text-[var(--bq-text)]">
                  <span className="bq-tour-check">
                    <Check className="size-3" aria-hidden />
                  </span>
                  {h}
                </li>
              ))}
            </ul>
          )}
          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <button ref={primaryRef} type="button" className="bq-tour-btn-primary flex-1" onClick={startTour}>
              <Compass className="size-4" aria-hidden />
              {welcome.primaryLabel}
            </button>
            <button type="button" className="bq-tour-btn-ghost" onClick={skip}>
              {welcome.secondaryLabel}
            </button>
          </div>
          <div className="mt-3 text-center text-[11px] text-[var(--bq-text-faint)]">
            {steps.length} short steps · about a minute · restart anytime from Help
          </div>
        </div>
      </div>
    );
  }

  if (mode === "done") {
    content = (
      <div className="bq-tour-modal-wrap" role="dialog" aria-modal="true" aria-labelledby="bq-tour-done-title">
        <div className="bq-tour-backdrop" onClick={() => setMode("idle")} />
        <div className="bq-tour-modal bq-hud bq-tour-pop text-center">
          <button type="button" className="bq-tour-close" aria-label="Close" onClick={() => setMode("idle")}>
            <X className="size-4" aria-hidden />
          </button>
          <div className="bq-tour-confetti" aria-hidden>
            {Array.from({ length: 18 }, (_, i) => (
              <span key={i} style={{ "--a": `${i * 20}deg`, "--d": `${(i % 3) * 60}ms` }} />
            ))}
          </div>
          <div className="bq-tour-emoji text-5xl" aria-hidden>
            🎉
          </div>
          <h2 id="bq-tour-done-title" className="bq-display mt-4 text-[28px] font-semibold uppercase tracking-[0.04em] text-[var(--bq-text)]">
            {completion.title}
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-[var(--bq-text-dim)]">{completion.body}</p>
          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <button ref={primaryRef} type="button" className="bq-tour-btn-primary flex-1" onClick={startFirstTest}>
              <Rocket className="size-4" aria-hidden />
              {completion.primaryLabel}
            </button>
            <button
              type="button"
              className="bq-tour-btn-ghost flex-1"
              onClick={() => window.dispatchEvent(new CustomEvent(TOUR_EVENTS.docs))}
            >
              <BookOpen className="size-4" aria-hidden />
              {completion.secondaryLabel}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (mode === "tour" && step) {
    const pos = mobile ? null : computeCardPosition(rect, cardSize, viewport, step.placement || "auto");
    const spot = rect && {
      top: Math.max(rect.top - PAD, -PAD),
      left: Math.max(rect.left - PAD, -PAD),
      width: Math.min(rect.width + PAD * 2, viewport.w + PAD * 2),
      height: Math.min(rect.height + PAD * 2, viewport.h + PAD * 2 - Math.max(rect.top - PAD, -PAD)),
    };
    const isLast = index === steps.length - 1;
    content = (
      <div className="bq-tour-layer">
        <div className="bq-tour-blocker" aria-hidden />
        <div className={`bq-tour-dim ${spot ? "opacity-0" : "opacity-100"}`} aria-hidden />
        {spot && <div className="bq-tour-spotlight" style={spot} aria-hidden />}

        <div
          ref={cardRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="bq-tour-step-title"
          className={`bq-tour-card bq-hud ${mobile ? "bq-tour-card-mobile" : ""}`}
          style={pos ? { top: pos.top, left: pos.left } : undefined}
        >
          <div key={step.id || index} className="bq-tour-step-in">
            <div className="flex items-center justify-between gap-3">
              <span className="bq-callout-tag">
                Step {index + 1} of {steps.length}
              </span>
              <button type="button" className="bq-tour-close static" aria-label="Skip tour" onClick={skip}>
                <X className="size-4" aria-hidden />
              </button>
            </div>
            <div className="mt-3 flex gap-1" aria-hidden>
              {steps.map((s, i) => (
                <span key={s.id || i} className="bq-tour-seg" data-state={i < index ? "done" : i === index ? "active" : "todo"} />
              ))}
            </div>
            <h3 id="bq-tour-step-title" className="bq-display mt-4 text-lg font-semibold uppercase tracking-[0.06em] text-[var(--bq-text)]">
              {step.title}
            </h3>
            <p className="mt-1.5 text-[13px] leading-6 text-[var(--bq-text-dim)]">{step.body}</p>
            <div className="sr-only" aria-live="polite">
              Step {index + 1} of {steps.length}
            </div>
          </div>

          <div className="mt-5 flex items-center justify-between gap-2">
            <button type="button" className="bq-tour-link whitespace-nowrap" onClick={skip}>
              Skip Tour
            </button>
            <div className="flex items-center gap-2">
              <button type="button" className="bq-tour-btn-ghost px-3" onClick={prev} disabled={index === 0} aria-label="Previous step">
                <ArrowLeft className="size-4" aria-hidden />
                <span className="hidden sm:inline">Previous</span>
              </button>
              <button ref={primaryRef} type="button" className="bq-tour-btn-primary px-4" onClick={next}>
                {isLast ? "Finish" : "Next"}
                {isLast ? <Check className="size-4" aria-hidden /> : <ArrowRight className="size-4" aria-hidden />}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return createPortal(content, document.body);
}
