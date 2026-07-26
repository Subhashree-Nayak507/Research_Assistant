import { useEffect, useRef, useState } from 'react'
import { openResearchSocket } from '../api'
import ProgressStream from '../components/ProgressStream'
import ReportView from '../components/ReportView'

export default function Research({ onSaved }) {
  const [query, setQuery] = useState('')
  const [running, setRunning] = useState(false)
  const [stage, setStage] = useState(null)
  const [log, setLog] = useState([])
  const [report, setReport] = useState(null)
  const [timing, setTiming] = useState(null)
  const [error, setError] = useState('')
  const socketRef = useRef(null)

  useEffect(() => {
    return () => socketRef.current?.close()
  }, [])

  function startResearch(e) {
    e.preventDefault()
    if (!query.trim() || running) return

    setRunning(true)
    setReport(null)
    setTiming(null)
    setError('')
    setLog([])
    setStage(null)

    const ws = openResearchSocket()
    socketRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ query }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.stage === 'error') {
        setError(data.message)
        setRunning(false)
        return
      }
      if (data.stage === 'report') {
        setReport(data.report)
        setTiming(data.timing)
        setRunning(false)
        onSaved?.() 
        return
      }
      setStage(data.stage)
      setLog((prev) => [...prev, data.message])
    }

    ws.onerror = () => {
      setError('Connection lost. Check that the backend is running and your session is valid.')
      setRunning(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-5 sm:px-8 py-10 sm:py-14 space-y-8">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal mb-2">New inquiry</p>
        <h1 className="font-display text-3xl sm:text-4xl text-parchment mb-2">What are we researching?</h1>
        <p className="text-parchment/50 text-sm sm:text-base">
          Four specialized agents — search, recall, verification, and synthesis — turn this into a cited report.
        </p>
      </div>

      <form onSubmit={startResearch} className="flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Competitive landscape for AI note-taking apps in India"
          className="flex-1 bg-slate-900 border border-slate-800 rounded-md px-4 py-3 text-parchment placeholder:text-parchment/30 focus-ring focus:border-signal transition-colors"
          disabled={running}
        />
        <button
          type="submit"
          disabled={running || !query.trim()}
          className="bg-signal text-ink font-medium rounded-md px-6 py-3 hover:brightness-110 disabled:opacity-50 transition focus-ring whitespace-nowrap"
        >
          {running ? 'Researching...' : 'Start research'}
        </button>
      </form>

      {error && (
        <p className="text-rust text-sm font-mono border border-rust/30 bg-rust/10 rounded-md px-3 py-2">{error}</p>
      )}

      {(running || log.length > 0) && <ProgressStream activeStage={stage} log={log} />}

      {timing && (
        <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-xs text-parchment/40 border-t border-slate-800 pt-4">
          <span className="text-signal">Generated in {timing.total_seconds}s</span>
          {Object.entries(timing)
            .filter(([key]) => key !== 'total_seconds')
            .map(([key, value]) => (
              <span key={key}>
                {key.replace('_agent', '')}: {value}s
              </span>
            ))}
        </div>
      )}

      {report && <ReportView report={report} />}
    </div>
  )
}
