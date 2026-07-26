const CONFIDENCE_STYLE = {
  high: 'bg-moss/15 text-moss border-moss/40',
  medium: 'bg-signal/15 text-signal border-signal/40',
  low: 'bg-rust/15 text-rust border-rust/40',
}

export default function ReportView({ report }) {
  if (!report) return null

  return (
    <article className="border border-slate-800 rounded-lg bg-slate-900/60 p-5 sm:p-8 space-y-8">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal mb-2">Executive summary</p>
        <p className="font-display text-lg sm:text-xl leading-relaxed text-parchment">{report.executive_summary}</p>
      </header>

      <section>
        <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal mb-3">Key findings</p>
        <ul className="space-y-3">
          {report.key_findings.map((f, i) => (
            <li key={i} className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4 border-b border-slate-800/70 pb-3 last:border-0">
              <span
                className={`shrink-0 self-start font-mono text-[10px] uppercase tracking-wider border rounded-full px-2 py-0.5 ${CONFIDENCE_STYLE[f.confidence] || CONFIDENCE_STYLE.low}`}
              >
                {f.confidence}
              </span>
              <div className="flex-1">
                <p className="text-parchment/90 text-sm sm:text-base">{f.claim}</p>
                {f.source_url && (
                  <a
                    href={f.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-mono text-parchment/40 hover:text-signal transition-colors break-all"
                  >
                    {f.source_url}
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal mb-3">Detailed analysis</p>
        <p className="text-parchment/80 text-sm sm:text-base leading-relaxed whitespace-pre-line">
          {report.detailed_analysis}
        </p>
      </section>

      {report.gaps_and_uncertainties?.length > 0 && (
        <section>
          <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-rust mb-3">Gaps &amp; uncertainties</p>
          <ul className="space-y-1.5">
            {report.gaps_and_uncertainties.map((g, i) => (
              <li key={i} className="text-sm text-parchment/70 flex gap-2">
                <span className="text-rust">⚠</span> {g}
              </li>
            ))}
          </ul>
        </section>
      )}

      {report.sources?.length > 0 && (
        <section>
          <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal mb-3">All sources</p>
          <ul className="space-y-1">
            {report.sources.map((s, i) => (
              <li key={i}>
                <a
                  href={s}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-mono text-parchment/50 hover:text-signal transition-colors break-all"
                >
                  {s}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}
