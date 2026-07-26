import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'

function statusDotClass(status) {
  switch (status) {
    case 'done': return 'bg-moss'
    case 'failed': return 'bg-rust'
    case 'running': return 'bg-signal animate-pulse'
    default: return 'bg-parchment/30'
  }
}

function timeAgo(iso) {
  if (!iso) return ''
  const diffSec = (Date.now() - new Date(iso).getTime()) / 1000
  if (diffSec < 60) return 'just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}

export default function Sidebar({ open, onClose, user, refreshKey, onLoggedOut }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { sessionId } = useParams()

  useEffect(() => {
    let cancelled = false
    setSessions([])
    setLoading(true)
    if (!user) {
      setLoading(false)
      return
    }
    api.history()
      .then((data) => { if (!cancelled) setSessions(data) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [refreshKey, user?.id, user?.email])

  async function logout() {
    await api.logout().catch(() => {})
    onLoggedOut?.()
    navigate('/login')
  }

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-ink/70 z-20 lg:hidden" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={`fixed lg:static inset-y-0 left-0 z-30 w-72 max-w-[85vw] shrink-0 flex flex-col
          bg-slate-900 border-r border-slate-800/80 transition-transform duration-200 ease-out
          ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}
      >
        <div className="px-5 py-4 border-b border-slate-800/80 flex items-baseline gap-2">
          <Link to="/" onClick={onClose} className="font-display text-xl tracking-tight text-parchment focus-ring rounded">
            Dossier
          </Link>
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-signal">research </span>
        </div>

        <div className="p-3">
          <Link
            to="/"
            onClick={() => {
              onNewInquiry?.()
              onClose?.()
            }}
            className="flex items-center justify-center gap-1.5 bg-signal text-ink font-medium text-sm rounded-md px-4 py-2.5 hover:brightness-110 transition focus-ring"
          >
            <span className="text-base leading-none">+</span> New inquiry
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 pb-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-parchment/30 px-3 pt-2 pb-1.5">
            Past inquiries
          </p>

          {loading && <p className="text-parchment/30 text-sm px-3 py-2">Loading…</p>}
          {!loading && sessions.length === 0 && (
            <p className="text-parchment/30 text-sm px-3 py-2">No research yet — start one above.</p>
          )}

          <ul className="space-y-1">
            {sessions.map((s) => (
              <li key={s.id}>
                <Link
                  to={`/session/${s.id}`}
                  onClick={onClose}
                  className={`flex items-start gap-2 rounded-md px-3 py-2.5 text-sm transition-colors focus-ring
                    ${sessionId === s.id ? 'bg-slate-800 text-parchment' : 'text-parchment/60 hover:bg-slate-850 hover:text-parchment'}`}
                >
                  <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${statusDotClass(s.status)}`} />
                  <span className="flex-1 min-w-0">
                    <span className="block truncate">{s.query}</span>
                    <span className="block font-mono text-[10px] text-parchment/30 mt-0.5">{timeAgo(s.created_at)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="border-t border-slate-800/80 p-3 flex items-center justify-between gap-2">
          <span className="text-parchment/50 text-xs truncate" title={user?.full_name}>
            {user?.full_name}
          </span>
          <button
            onClick={logout}
            className="font-mono text-xs uppercase tracking-wider text-parchment/60 hover:text-signal transition-colors focus-ring rounded px-2 py-1 shrink-0"
          >
            Sign out
          </button>
        </div>
      </aside>
    </>
  )
}