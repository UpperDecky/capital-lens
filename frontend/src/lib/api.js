/**
 * API client — all requests go through here.
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
    throw new Error(err.detail || 'Request failed')
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

  // Themes
  getThemes: () => request('/themes'),

  // Search
  search: (q) => request(`/search?q=${encodeURIComponent(q)}`),

  // Auth
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

  // Health
  health: () => request('/health'),

  // Admin — pass VITE_ADMIN_SECRET from .env if set
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
