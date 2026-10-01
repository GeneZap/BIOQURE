# Deployment

Deploy the Python inference service with the locked runtime dependencies and the verified
model artifacts, public pool, immutable lock, and `backend/inference_service/`. Build the
Vite frontend with `VITE_API_BASE_URL` set to the deployed API origin. Configure explicit
`BIOQURE_CORS_ORIGINS`; do not use wildcard production CORS.

This is a research demonstration only. The output is not a medical diagnosis and must not
be used for clinical decisions.# Deployment guide (Vercel + Render/Fly)

## Architecture (incremental, matches current code)

| Layer | Target | Notes |
|--------|--------|--------|
| Frontend | **Vercel** (static) | Build with `VITE_API_BASE_URL` pointing to your **HTTPS** API. |
| Backend | **Docker** on **Render** or **Fly.io** | `Dockerfile` at repo root; exposes `PORT` / `8000`. |
| Dataset pools | **Filesystem** under `GENEZAP_DATASETS_ROOT` | Mount a **persistent volume** or accept data loss on sleep (free tier). |
| Models | **In image** via `CV_HACKATHON_MODEL_DATASET` + `backend/` | Large; consider pruning unused assets later. |

Future: replace `GENEZAP_DATASETS_ROOT` with S3/R2 + PostgreSQL metadata — call sites stay env-driven.

---

## 1. Backend (Render example)

1. Create **Web Service** → **Docker** repo.
2. **Root directory**: repository root (where `Dockerfile` lives).
3. **Health check path**: `/ready` (writable volume) or `/health/live` if volume not yet attached.
4. **Environment variables** (minimum):

| Variable | Example |
|----------|---------|
| `GENEZAP_ENV` | `production` |
| `GENEZAP_CORS_ORIGINS` | `https://<your-project>.vercel.app` |
| `GENEZAP_DATASETS_ROOT` | `/data/datasets` |
| `GENEZAP_CV_ARTIFACT_ROOT` | Optional: path to `CV_HACKATHON_MODEL_DATASET` tree for integrated engine (default: sibling of `backend/`) |
| `GENEZAP_MAX_UPLOAD_MB` | `100` (tune for host) |

5. **Disk**: Add a **persistent disk** mounted at `/data/datasets` if you need pool survival across deploys.

**Start command** (already in Dockerfile):

`uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## 2. Backend (Fly.io sketch)

```bash
fly launch --dockerfile Dockerfile --copy-config
fly volumes create genezap_data --size 3
# Mount volume at /data/datasets in fly.toml [mounts] section
fly secrets set GENEZAP_ENV=production GENEZAP_CORS_ORIGINS=https://...
```

---

## 3. Frontend (Vercel)

1. **Project root**: `frontend/`
2. **Build**: `npm run build`
3. **Output**: `dist/` (Vite default)
4. **Environment (Production / Preview)**:

| Name | Value |
|------|--------|
| `VITE_API_BASE_URL` | `https://api.yourdomain.com` (no trailing slash) |

5. **Redeploy** whenever the API origin changes (Vite inlines `VITE_*` at build time).

`vercel.json` in `frontend/` enables SPA fallback for client-side routing.

---

## 4. Connecting frontend ↔ backend

1. API must be **HTTPS** (Vercel pages are HTTPS; mixed content blocked if API is HTTP-only).
2. Set **`GENEZAP_CORS_ORIGINS`** to your Vercel origin(s).
3. Confirm **`GET https://api.../ready`** returns `200` before sharing the UI.

---

## 5. Testing after deploy

```bash
curl -sS https://<api>/health/live
curl -sS https://<api>/ready
curl -sS https://<api>/datasets/config/hints
```

Then run one **`POST /analyze`** with a small FASTA.

---

## 6. Free-tier limitations (expected)

| Symptom | Cause |
|---------|--------|
| Cold start 30–90s | TensorFlow + model load |
| 502 / timeout on large FASTA | Gateway timeout < inference time |
| Pools disappear | Ephemeral disk without volume |
| Batch job lost | Process restart / second replica |
| OOM | RAM limit < TF + sequence |

Tune **`GENEZAP_MAX_UPLOAD_MB`**, **`GENEZAP_MAX_BATCH_FILES`**, and **`GENEZAP_SKIP_TENSORFLOW=1`** only if you accept degraded V3.

---

## 7. Security checklist (demo → production)

- Set explicit **`GENEZAP_CORS_ORIGINS`** (drop wildcard when you add cookies/auth).
- Keep **`GENEZAP_ALLOW_DATASET_PATH_IMPORT`** off outside dev machines.
- Add **auth** + **rate limits** before public exposure (not yet in codebase).
- Do not expose **`/datasets/config/hints`** publicly if it leaks paths you care about (low risk today).
