/**
 * API base URL (Vite: VITE_API_BASE_URL, no trailing slash).
 * Production builds should set this in Vercel → Environment Variables before `npm run build`.
 */
const raw = import.meta.env.VITE_API_BASE_URL?.trim()
const isProd = import.meta.env.PROD === true

if (isProd && !raw) {
  // eslint-disable-next-line no-console
  console.error(
    '[GeneZap] VITE_API_BASE_URL is not set. Add it in Vercel (or .env.production) so the UI can reach your deployed API.',
  )
}

const fallbackDev = 'http://localhost:8000'
export const API_BASE = String(raw || fallbackDev).replace(/\/$/, '')
export const ANALYZE_URL = `${API_BASE}/analyze`

/** True when VITE_API_BASE_URL was provided (recommended for deployed sites). */
export function hasExplicitApiBase() {
  return Boolean(raw)
}
