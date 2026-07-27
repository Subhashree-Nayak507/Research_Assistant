
const sameOriginWs =
  typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
    : ''

const API_BASE =
  import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? 'http://localhost:8001' : '')
const WS_BASE =
  import.meta.env.VITE_WS_BASE ?? (import.meta.env.DEV ? 'ws://localhost:8001' : sameOriginWs)


async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  register: (email, password, full_name) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, full_name }) }),
  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),
  history: () => request('/research/history'),
  knowledge: () => request('/research/knowledge'),
}

export function openResearchSocket() {
  // Cookie rides along automatically on the WS handshake for allowed origins.
  return new WebSocket(`${WS_BASE}/research/ws`)
}