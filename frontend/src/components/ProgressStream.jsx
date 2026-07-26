const STAGES = [
  { key: 'search', label: 'Search', desc: 'Scanning live sources' },
  { key: 'rag', label: 'Recall', desc: 'Checking knowledge base' },
  { key: 'synthesize', label: 'Draft', desc: 'Writing the report' },
  { key: 'critic', label: 'Verify', desc: 'Flagging unsupported claims' },
  { key: 'ingest', label: 'Remember', desc: 'Saving for next time' },
  { key: 'done', label: 'Done', desc: 'Report ready' },
]

export default function ProgressStream({ activeStage, log }) {
  const activeIndex = STAGES.findIndex((s) => s.key === activeStage)

  return (
    <div className="border border-slate-800 rounded-lg bg-slate-900/60 p-5 sm:p-6">
      <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal mb-5">Pipeline status</p>

      <ol className="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-2">
        {STAGES.map((stage, i) => {
          const state =
            activeIndex < 0 ? 'idle' : i < activeIndex ? 'done' : i === activeIndex ? 'active' : 'pending'
          return (
            <li key={stage.key} className="flex sm:flex-col sm:items-center flex-1 gap-3 sm:gap-2 sm:text-center">
              <div
                className={[
                  'w-7 h-7 shrink-0 rounded-full border flex items-center justify-center font-mono text-xs transition-colors',
                  state === 'done' && 'bg-moss/20 border-moss text-moss',
                  state === 'active' && 'bg-signal/20 border-signal text-signal animate-pulse',
                  state === 'pending' && 'border-slate-700 text-parchment/30',
                  state === 'idle' && 'border-slate-700 text-parchment/30',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                {state === 'done' ? '✓' : i + 1}
              </div>
              <div>
                <p
                  className={[
                    'text-sm font-medium',
                    state === 'active' ? 'text-signal' : state === 'done' ? 'text-parchment' : 'text-parchment/40',
                  ].join(' ')}
                >
                  {stage.label}
                </p>
                <p className="text-xs text-parchment/40 hidden sm:block">{stage.desc}</p>
              </div>
            </li>
          )
        })}
      </ol>

      {log.length > 0 && (
        <div className="mt-6 pt-5 border-t border-slate-800 space-y-1.5 max-h-40 overflow-y-auto">
          {log.map((entry, i) => (
            <p key={i} className="font-mono text-xs text-parchment/50">
              <span className="text-signal">›</span> {entry}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
