import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import ReportView from '../components/ReportView'

export default function SessionView() {
  const { sessionId } = useParams()
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    api.history()
      .then((sessions) => {
        if (cancelled) return
        const match = sessions.find((s) => s.id === sessionId)
        if (!match) setError('That research session was not found.')
        else setSession(match)
      })
      .catch(() => { if (!cancelled) setError('Could not load that session.') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [sessionId])

  const report = session?.report_json ? JSON.parse(session.report_json) : null

  return (
    <div className="max-w-3xl mx-auto px-5 sm:px-8 py-10 sm:py-14 space-y-8">
      <div>
        <Link to="/" className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal hover:text-parchment transition-colors focus-ring rounded">
          ← New inquiry
        </Link>
        {session && <h1 className="font-display text-2xl sm:text-3xl text-parchment mt-3">{session.query}</h1>}
      </div>

      {loading && <p className="text-parchment/40 text-sm">Loading…</p>}
      {error && (
        <p className="text-rust text-sm font-mono border border-rust/30 bg-rust/10 rounded-md px-3 py-2">{error}</p>
      )}
      {session && session.status === 'running' && (
        <p className="text-signal text-sm font-mono border border-signal/30 bg-signal/10 rounded-md px-3 py-2">
          This inquiry is still running — check back shortly.
        </p>
      )}
      {session && session.status === 'failed' && !report && (
        <p className="text-rust text-sm font-mono border border-rust/30 bg-rust/10 rounded-md px-3 py-2">
          This inquiry failed before producing a report.
        </p>
      )}

      {report && <ReportView report={report} />}
    </div>
  )
}
