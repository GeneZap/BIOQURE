/**
 * Parse FastAPI-style JSON error bodies from fetch Response.
 */
export async function readApiErrorDetail(response) {
  try {
    const data = await response.clone().json()
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail.map((d) => (typeof d === 'object' && d?.msg ? d.msg : String(d))).join(' ')
    }
    if (data.detail && typeof data.detail === 'object') {
      return JSON.stringify(data.detail)
    }
    return response.statusText || `HTTP ${response.status}`
  } catch {
    return response.statusText || `HTTP ${response.status}`
  }
}

export function describeFetchFailure(err, fallback = 'Network error') {
  if (!err) return fallback
  if (err instanceof TypeError && String(err.message).toLowerCase().includes('fetch')) {
    return 'Could not reach the API (offline, wrong URL, or CORS). Check VITE_API_BASE_URL and that the backend is running.'
  }
  return err.message || fallback
}
