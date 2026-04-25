/**
 * API client -- all requests go through here.
 * The Vite proxy forwards /feed, /entities, etc. to http://localhost:8000
 */

const BASE = ''

async function request(path, options = {}) {
  const token = localStorage.getItem('cl_token')
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const msg = typeof err.detail === 'string' ? err.detail : err.detail?.message || 'Request failed'
    const error = new Error(msg)
    error.status = res.status
    error.detail = err.detail
    throw error
  }
  return res.json()
}

export const api = {
  // Feed
  getFeed: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''))
    ).toString()
    return request(`/feed${qs ? '?' + qs : ''}`)
  },

  // Entities
  getEntities: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''))
    ).toString()
    return request(`/entities${qs ? '?' + qs : ''}`)
  },
  getEntity: (id) => request(`/entities/${id}`),
  getEntityTimeseries: (id, days = 30) => request(`/entities/${id}/timeseries?days=${days}`),

  // Themes
  getThemes: () => request('/themes'),

  // Search
  search: (q) => request(`/search?q=${encodeURIComponent(q)}`),

  // Auth -- standard
  register: (email, password) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  login: (email, password) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  // Auth -- MFA setup (requires full JWT in localStorage)
  mfaSetup: () =>
    request('/auth/mfa/setup', { method: 'POST' }),

  mfaVerify: (code) =>
    request('/auth/mfa/verify', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),

  // MFA login challenge -- pendingToken is NOT stored in localStorage;
  // it is passed explicitly to avoid polluting the standard auth header.
  mfaChallenge: (code, pendingToken) =>
    request('/auth/mfa/challenge', {
      method: 'POST',
      body: JSON.stringify({ code }),
      headers: { Authorization: `Bearer ${pendingToken}` },
    }),

  mfaDisable: (password, code) =>
    request('/auth/mfa/disable', {
      method: 'POST',
      body: JSON.stringify({ password, code }),
    }),

  // Profile
  getMe: () => request('/auth/me'),
  acceptDisclaimer: () => request('/auth/accept-disclaimer', { method: 'POST' }),

  // Intel feed
  getIntelFeed: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''))
    ).toString()
    return request(`/feed/intel${qs ? '?' + qs : ''}`)
  },
  getIntelCounts: () => request('/feed/intel/counts'),
  getAlerts: () => request('/feed/alerts'),

  // Cash flow
  getCashFlows: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''))
    ).toString()
    return request(`/cashflow${qs ? '?' + qs : ''}`)
  },
  getCashFlowLive: (hours = 24) => request(`/cashflow/live?limit=50&hours=${hours}`),
  getCashFlowStats: () => request('/cashflow/stats'),
  getCashFlowVolume: (days = 7) => request(`/cashflow/volume?days=${days}`),

  // Health
  health: () => request('/health'),

  // Admin -- pass VITE_ADMIN_SECRET from .env if set
  adminIngest: () => request('/admin/ingest', {
    method: 'POST',
    headers: import.meta.env.VITE_ADMIN_SECRET
      ? { 'X-Admin-Secret': import.meta.env.VITE_ADMIN_SECRET }
      : {},
  }),
  adminEnrich: () => request('/admin/enrich', {
    method: 'POST',
    headers: import.meta.env.VITE_ADMIN_SECRET
      ? { 'X-Admin-Secret': import.meta.env.VITE_ADMIN_SECRET }
      : {},
  }),
}
