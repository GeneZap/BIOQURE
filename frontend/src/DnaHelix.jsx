import React, { useEffect, useRef, useState } from "react";
import { Minus, Pause, Play, Plus } from "lucide-react";

/**
 * Animated particle double-helix hero, modeled on the reference genomic
 * dashboard: two thick, glowing silver backbones built from tens of
 * thousands of lit particles (WebGL), dense base-pair bars between them,
 * a tilted S-curved axis that dissolves into dust at both ends, and
 * orange / green gene segments with HUD callouts naming BIOQURE stages.
 */

const CALLOUTS = [
  {
    id: "GF-08",
    t: 0.3,
    strand: 0,
    side: "left",
    cardY: 0.2,
    color: [1.0, 0.47, 0.16],
    label: "6–8 GENE FUNNEL",
    sub: "Train-only feature selection",
    status: "SELECTED",
    tone: "orange",
  },
  {
    id: "ZZ-02",
    t: 0.5,
    strand: 1,
    side: "right",
    cardY: 0.5,
    color: [0.22, 1.0, 0.45],
    label: "ZZ FEATURE MAP",
    sub: "Quantum angle encoding",
    status: "STABLE",
    tone: "green",
  },
  {
    id: "VQC-01",
    t: 0.76,
    strand: 0,
    side: "left",
    cardY: 0.8,
    color: [1.0, 0.47, 0.16],
    label: "VQC INFERENCE",
    sub: "Qiskit Aer simulator",
    status: "SIMULATED",
    tone: "orange",
  },
];

const TAU = Math.PI * 2;
const TURNS = 2.3;
// < PI gives the major/minor groove look, so both strands read separately
const STRAND_OFFSET = Math.PI * 0.8;
const TILT = 0.2;
const FOCAL = 1100;
const SEGMENT_HALF = 0.05;
const CARD_INSET = 0.13;
const SILVER = [0.84, 0.88, 0.95];
const STRIDE = 11;

/* ---------- animation timing ----------
 * Rotation is a pure angle (wrapped to one turn), so it has no cycle seam.
 * Every other time-driven effect (twinkle, dust drift, node pulse) runs an
 * integer number of cycles per LOOP_MS, so wrapping the clock is invisible
 * and keeps shader inputs small (no float precision drift on long sessions).
 */
const SPIN_RATE = 0.00038; // rad per ms
const LOOP_MS = 600000;
const PULSE_CYCLES = 382; // ≈ 1.57 s per pulse
const FRAME = 1000 / 60;

/* ---------- shared geometry (JS mirror of the vertex shader) ---------- */

function getGeometry(w, h, zoom, pointerX) {
  const len = h * 0.9 * zoom;
  const R = Math.min(w * 0.17, h * 0.12) * zoom;
  return {
    len,
    top: h / 2 - len / 2,
    R,
    tube: R * 0.2,
    cx: w / 2 + pointerX * 8,
    cy: h / 2,
  };
}

function strandPoint(t, s, g, angle) {
  const phi = t * TAU * TURNS + angle + s * STRAND_OFFSET;
  const ax = g.cx + Math.sin(t * Math.PI * 1.4 + 0.5) * g.R * 0.45;
  return [ax + g.R * Math.cos(phi), g.top + t * g.len, g.R * Math.sin(phi)];
}

function project([x, y, z], g) {
  const sc = FOCAL / (FOCAL - z);
  const dx = (x - g.cx) * sc;
  const dy = (y - g.cy) * sc;
  const c = Math.cos(TILT);
  const sn = Math.sin(TILT);
  return [g.cx + dx * c - dy * sn, g.cy + dx * sn + dy * c];
}

/* ---------- shaders ---------- */

const VERT = `
attribute vec4 a_a; // t, kind, strand, theta
attribute vec4 a_b; // r, u, size, seed
attribute vec3 a_color;
uniform vec2 u_res;
uniform float u_dpr, u_angle, u_phase, u_top, u_len, u_R, u_tube, u_cx, u_cy, u_tilt, u_offset, u_turns, u_focal;
varying vec3 v_color;
varying float v_alpha;
varying float v_soft;
const float TAU = 6.2831853;

vec3 strandPoint(float t, float s, out float phi) {
  phi = t * TAU * u_turns + u_angle + s * u_offset;
  float ax = u_cx + sin(t * 3.1415927 * 1.4 + 0.5) * u_R * 0.45;
  return vec3(ax + u_R * cos(phi), u_top + t * u_len, u_R * sin(phi));
}

vec3 hash3(float s) {
  return fract(sin(vec3(s * 127.1, s * 311.7, s * 74.7)) * 43758.5453);
}

void main() {
  float t = a_a.x;
  float kind = a_a.y;
  float s = a_a.z;
  float theta = a_a.w;
  float r = a_b.x;
  float u = a_b.y;
  float size = a_b.z;
  float seed = a_b.w;

  vec3 p;
  vec3 n = vec3(0.0, 0.0, 1.0);
  float lit = 1.0;
  float alpha = 1.0;
  float tw = 0.6 + 0.4 * sin(TAU * u_phase * floor(84.0 + seed * 210.0) + seed * 60.0);
  vec3 L = normalize(vec3(-0.35, -0.55, 0.76));
  v_soft = 0.0;

  if (kind < 0.5) {
    // backbone strand: lit tube of particles
    float phi;
    vec3 c = strandPoint(t, s, phi);
    float dphi = TAU * u_turns;
    vec3 T = normalize(vec3(-u_R * dphi * sin(phi), u_len, u_R * dphi * cos(phi)));
    vec3 N1 = vec3(cos(phi), 0.0, sin(phi));
    vec3 N2 = normalize(cross(T, N1));
    n = cos(theta) * N1 + sin(theta) * N2;
    p = c + n * (u_tube * r);
    float diff = max(dot(n, L), 0.0);
    lit = 0.3 + 1.1 * diff + pow(1.0 - abs(n.z), 3.0) * 0.3;
    alpha = 0.85;
  } else if (kind < 1.5) {
    // base-pair rung between the two backbones
    float pa;
    float pb;
    vec3 A = strandPoint(t, 0.0, pa);
    vec3 B = strandPoint(t, 1.0, pb);
    vec3 d = normalize(B - A);
    vec3 up = vec3(0.0, 1.0, 0.0);
    vec3 side = normalize(cross(d, up));
    n = cos(theta) * up + sin(theta) * side;
    p = mix(A, B, mix(0.06, 0.94, u)) + n * (u_tube * 0.16 * r);
    float diff = max(dot(n, L), 0.0);
    lit = 0.65 + 0.7 * diff;
    alpha = 1.0;
  } else if (kind < 2.5) {
    // floating dust
    p = vec3(u * u_res.x, fract(t - u_phase * floor(1.0 + seed * 4.0)) * u_res.y, (r - 0.5) * 300.0);
    alpha = 0.35;
  } else {
    // soft bloom around the backbone
    float phi;
    p = strandPoint(t, s, phi);
    alpha = 0.05;
    v_soft = 1.0;
    tw = 1.0;
  }

  if (kind < 1.5 || kind > 2.5) {
    // fade + dissolve into particles at both ends
    float e = smoothstep(0.0, 0.08, t) * smoothstep(1.0, 0.88, t);
    p += (hash3(seed) - 0.5) * (1.0 - e) * u_R * 1.1;
    alpha *= mix(0.25, 1.0, e);
    float near = clamp(p.z / u_R * 0.5 + 0.5, 0.0, 1.0);
    alpha *= 0.6 + 0.4 * near;
  }

  float spec = pow(max(lit - 0.9, 0.0) * 3.0, 2.0);
  v_color = mix(a_color * lit, vec3(1.0), clamp(spec, 0.0, 0.8));
  v_alpha = alpha * tw;

  float sc = u_focal / (u_focal - p.z);
  vec2 dd = (p.xy - vec2(u_cx, u_cy)) * sc;
  float ct = cos(u_tilt);
  float st = sin(u_tilt);
  vec2 q = vec2(u_cx, u_cy) + vec2(dd.x * ct - dd.y * st, dd.x * st + dd.y * ct);
  gl_Position = vec4(q.x / u_res.x * 2.0 - 1.0, 1.0 - q.y / u_res.y * 2.0, 0.0, 1.0);
  gl_PointSize = max(size * sc * u_dpr, 1.0);
}
`;

const FRAG = `
precision mediump float;
varying vec3 v_color;
varying float v_alpha;
varying float v_soft;
void main() {
  float d = length(gl_PointCoord - 0.5) * 2.0;
  if (d > 1.0) discard;
  float a = v_soft > 0.5 ? pow(1.0 - d, 2.0) : 1.0 - smoothstep(0.25, 1.0, d);
  gl_FragColor = vec4(v_color * v_alpha * a, v_alpha * a);
}
`;

/* ---------- particle buffer ---------- */

function segmentColor(t, s) {
  for (const c of CALLOUTS) {
    if (c.strand !== s) continue;
    const d = Math.abs(t - c.t);
    if (d < SEGMENT_HALF) {
      const k = Math.min(1, (SEGMENT_HALF - d) / 0.012);
      return SILVER.map((v, i) => v + (c.color[i] - v) * k);
    }
  }
  return null;
}

function buildParticles(tubeScale) {
  const out = [];
  const push = (t, kind, s, theta, r, u, size, color) => {
    out.push(t, kind, s, theta, r, u, size, Math.random(), color[0], color[1], color[2]);
  };

  const SAMPLES = Math.round(1000 * tubeScale);
  const PER = 18;
  for (let s = 0; s < 2; s++) {
    for (let i = 0; i < SAMPLES; i++) {
      for (let k = 0; k < PER; k++) {
        const t = Math.random();
        const stray = Math.random() < 0.06;
        const r = stray ? 1 + Math.random() * 0.9 : 0.5 + 0.5 * Math.sqrt(Math.random());
        const big = Math.random() < 0.04;
        const size = big ? 2.6 + Math.random() * 1.6 : 1 + Math.random() * 1.2;
        const seg = segmentColor(t, s);
        push(t, 0, s, Math.random() * TAU, r, 0, stray ? size * 0.8 : size, seg || SILVER);
      }
    }
    for (let i = 0; i < 380; i++) {
      const t = Math.random();
      push(t, 3, s, 0, 0, 0, 26 + Math.random() * 18, segmentColor(t, s) || [0.6, 0.72, 0.95]);
    }
  }

  const RUNGS = Math.round(TURNS * 10.5);
  const PER_RUNG = Math.round(650 * tubeScale);
  for (let i = 0; i < RUNGS; i++) {
    const t = (i + 0.5) / RUNGS;
    const rungColor = segmentColor(t, 0) || segmentColor(t, 1) || SILVER;
    for (let k = 0; k < PER_RUNG; k++) {
      const r = 0.4 + 0.6 * Math.sqrt(Math.random());
      push(t, 1, 0, Math.random() * TAU, r, Math.random(), 1.2 + Math.random() * 1.2, rungColor);
    }
  }

  for (let i = 0; i < 320; i++) {
    push(Math.random(), 2, 0, 0, Math.random(), Math.random(), 1 + Math.random() * 2.2, [0.55, 0.68, 1]);
  }

  return new Float32Array(out);
}

function compile(gl, type, src) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    // eslint-disable-next-line no-console
    console.error("[DnaHelix] shader error:", gl.getShaderInfoLog(sh));
    gl.deleteShader(sh);
    return null;
  }
  return sh;
}

export default function DnaHelix({ className = "" }) {
  const wrapRef = useRef(null);
  const glCanvasRef = useRef(null);
  const overlayRef = useRef(null);
  const stateRef = useRef({ zoom: 1, paused: false, pointerX: 0, pointerY: 0, drag: null, spin: 0 });
  const [zoom, setZoom] = useState(1);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    stateRef.current.zoom = zoom;
  }, [zoom]);

  useEffect(() => {
    stateRef.current.paused = paused;
  }, [paused]);

  useEffect(() => {
    const wrap = wrapRef.current;
    const glCanvas = glCanvasRef.current;
    const overlay = overlayRef.current;
    if (!wrap || !glCanvas || !overlay) return undefined;

    const gl = glCanvas.getContext("webgl", { alpha: true, premultipliedAlpha: true, antialias: false });
    const ctx = overlay.getContext("2d");
    if (!gl || !ctx) return undefined;

    const vs = compile(gl, gl.VERTEX_SHADER, VERT);
    const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return undefined;
    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    gl.useProgram(program);

    const lowPower = (navigator.hardwareConcurrency || 8) <= 4 || window.innerWidth < 768;
    const data = buildParticles(lowPower ? 0.6 : 1);
    const count = data.length / STRIDE;
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);

    const attr = (name, size, offset) => {
      const loc = gl.getAttribLocation(program, name);
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, STRIDE * 4, offset * 4);
    };
    attr("a_a", 4, 0);
    attr("a_b", 4, 4);
    attr("a_color", 3, 8);

    const U = {};
    ["u_res", "u_dpr", "u_angle", "u_phase", "u_top", "u_len", "u_R", "u_tube", "u_cx", "u_cy", "u_tilt", "u_offset", "u_turns", "u_focal"].forEach(
      (name) => {
        U[name] = gl.getUniformLocation(program, name);
      }
    );
    gl.uniform1f(U.u_tilt, TILT);
    gl.uniform1f(U.u_offset, STRAND_OFFSET);
    gl.uniform1f(U.u_turns, TURNS);
    gl.uniform1f(U.u_focal, FOCAL);

    gl.disable(gl.DEPTH_TEST);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE);

    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    let w = 0;
    let h = 0;
    let dpr = 1;
    let raf = 0;
    let visible = true;
    let last = 0;
    let angle = 0;
    let time = 0;
    let speed = reduceMotion ? 0 : 1;
    let px = 0;
    let zoomNow = stateRef.current.zoom;
    let quality = 1;
    let slowFrames = 0;
    const strokes = CALLOUTS.map((c) => `rgb(${c.color.map((v) => Math.round(v * 255)).join(",")})`);

    const resize = () => {
      const rect = wrap.getBoundingClientRect();
      dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2) * quality);
      w = rect.width;
      h = rect.height;
      for (const c of [glCanvas, overlay]) {
        c.width = Math.round(w * dpr);
        c.height = Math.round(h * dpr);
        c.style.width = `${w}px`;
        c.style.height = `${h}px`;
      }
      gl.viewport(0, 0, glCanvas.width, glCanvas.height);
    };

    const draw = (now) => {
      const gap = last ? now - last : FRAME;
      last = now;
      // After a tab switch / scroll-back, resume from where we were instead of jumping.
      const dt = gap > 250 ? FRAME : gap;
      const k = dt / FRAME;
      const st = stateRef.current;

      // Ease speed, pointer parallax and zoom so nothing ever snaps.
      const target = st.paused || reduceMotion ? 0 : 1;
      speed += (target - speed) * (1 - Math.exp(-dt / 260));
      px += (st.pointerX - px) * (1 - Math.exp(-dt / 140));
      zoomNow += (st.zoom - zoomNow) * (1 - Math.exp(-dt / 120));

      angle = (angle - dt * SPIN_RATE * speed - st.spin * k) % TAU;
      st.spin *= Math.pow(0.92, k);
      time = (time + dt * speed) % LOOP_MS;
      const phase = time / LOOP_MS;

      // Adaptive resolution: on GPUs that can't keep up, render fewer pixels.
      if (dpr > 1 && gap <= 250) {
        slowFrames = gap > 28 ? slowFrames + 1 : Math.max(0, slowFrames - 2);
        if (slowFrames > 90) {
          quality *= 0.8;
          slowFrames = 0;
          resize();
        }
      }

      const g = getGeometry(w, h, zoomNow, px);
      const view = angle + px * 0.15;

      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform2f(U.u_res, w, h);
      gl.uniform1f(U.u_dpr, dpr);
      gl.uniform1f(U.u_angle, view);
      gl.uniform1f(U.u_phase, phase);
      gl.uniform1f(U.u_top, g.top);
      gl.uniform1f(U.u_len, g.len);
      gl.uniform1f(U.u_R, g.R);
      gl.uniform1f(U.u_tube, g.tube);
      gl.uniform1f(U.u_cx, g.cx);
      gl.uniform1f(U.u_cy, g.cy);
      gl.drawArrays(gl.POINTS, 0, count);

      // Callout node rings + connector lines to the HUD cards
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      for (let i = 0; i < CALLOUTS.length; i++) {
        const c = CALLOUTS[i];
        const [x, y] = project(strandPoint(c.t, c.strand, g, view), g);
        const pulse = 0.5 + 0.5 * Math.sin(TAU * phase * PULSE_CYCLES + c.t * 10);
        const cardX = c.side === "left" ? w * (0.5 - CARD_INSET) - 2 : w * (0.5 + CARD_INSET) + 2;
        const anchorY = h * c.cardY;

        ctx.strokeStyle = "rgba(225,232,245,0.6)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(cardX, anchorY);
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(x, y, 10 + pulse * 4, 0, TAU);
        ctx.globalAlpha = 0.3 + pulse * 0.45;
        ctx.strokeStyle = strokes[i];
        ctx.lineWidth = 1.2;
        ctx.stroke();
        ctx.globalAlpha = 1;

        ctx.beginPath();
        ctx.arc(x, y, 6.5, 0, TAU);
        ctx.strokeStyle = "rgba(255,255,255,0.95)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(x, y, 2.2, 0, TAU);
        ctx.fillStyle = "#fff";
        ctx.fill();
      }

      if (visible) raf = requestAnimationFrame(draw);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(wrap);
    resize();

    const io = new IntersectionObserver(([entry]) => {
      const was = visible;
      visible = entry.isIntersecting;
      if (visible && !was) {
        last = 0;
        raf = requestAnimationFrame(draw);
      }
    });
    io.observe(wrap);

    const onMove = (e) => {
      const rect = wrap.getBoundingClientRect();
      const st = stateRef.current;
      st.pointerX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      st.pointerY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
      if (st.drag !== null) {
        st.spin = -(e.clientX - st.drag) * 0.004;
        st.drag = e.clientX;
      }
    };
    const onDown = (e) => {
      stateRef.current.drag = e.clientX;
    };
    const onUp = () => {
      stateRef.current.drag = null;
    };
    const onLeave = () => {
      stateRef.current.pointerX = 0;
      stateRef.current.pointerY = 0;
      stateRef.current.drag = null;
    };
    wrap.addEventListener("pointermove", onMove);
    wrap.addEventListener("pointerdown", onDown);
    window.addEventListener("pointerup", onUp);
    wrap.addEventListener("pointerleave", onLeave);

    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      wrap.removeEventListener("pointermove", onMove);
      wrap.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      wrap.removeEventListener("pointerleave", onLeave);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
    };
  }, []);

  return (
    <div
      ref={wrapRef}
      className={`bq-helix-stage relative h-full w-full min-h-[560px] cursor-grab select-none active:cursor-grabbing ${className}`}
      style={{
        background:
          "radial-gradient(ellipse 45% 55% at 50% 50%, rgba(110,150,220,0.16), rgba(10,14,20,0) 70%)",
      }}
    >
      <canvas ref={glCanvasRef} className="absolute inset-0" aria-hidden />
      <canvas ref={overlayRef} className="pointer-events-none absolute inset-0" aria-hidden />

      {CALLOUTS.map((c, i) => (
        <div
          key={c.id}
          className="bq-callout pointer-events-none absolute w-[40%] max-w-[200px]"
          style={{
            top: `${c.cardY * 100}%`,
            [c.side === "left" ? "right" : "left"]: `${(0.5 + CARD_INSET) * 100}%`,
            transform: "translateY(-50%)",
            animationDelay: `${0.4 + i * 0.25}s`,
          }}
        >
          <div className={`flex ${c.side === "left" ? "justify-end" : "justify-start"}`}>
            <span className="bq-callout-tag">{c.id}</span>
          </div>
          <div className="bq-hud mt-1 px-3 py-2.5">
            <div className="bq-display text-[11px] font-semibold tracking-[0.08em] text-[var(--bq-text)]">
              {c.label}
            </div>
            <div className="mt-0.5 text-[10px] leading-4 text-[var(--bq-text-faint)]">{c.sub}</div>
            <span className={`bq-status bq-status-${c.tone} mt-2`}>{c.status}</span>
          </div>
        </div>
      ))}

      <div className="absolute bottom-2 right-2 z-10 flex items-end gap-2">
        <button
          type="button"
          onClick={() => setPaused((p) => !p)}
          className="bq-icon-btn"
          aria-label={paused ? "Resume helix rotation" : "Pause helix rotation"}
        >
          {paused ? <Play className="size-4" aria-hidden /> : <Pause className="size-4" aria-hidden />}
        </button>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(1.25, +(z + 0.1).toFixed(2)))}
            className="bq-icon-btn"
            aria-label="Zoom in"
          >
            <Plus className="size-4" aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.7, +(z - 0.1).toFixed(2)))}
            className="bq-icon-btn"
            aria-label="Zoom out"
          >
            <Minus className="size-4" aria-hidden />
          </button>
        </div>
      </div>
    </div>
  );
}
