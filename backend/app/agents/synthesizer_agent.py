"""
Synthesizer Agent
-----------------
Job: turn verified findings into a clean, consistently structured report
using Pydantic structured output (ResearchReport). Real LLM call, real
grounding in what Search + RAG actually found — no invented facts.

If the Critic Agent flagged issues on a previous pass, they're passed in
so the Synthesizer can correct itself instead of repeating the same
unsupported claims (this is the "reflection loop" in practice).
"""
import logging

from langchain_core.prompts import PromptTemplate

from app.schemas import ResearchReport
from app.agents.llm_client import generate_json, LLMUnavailableError

logger = logging.getLogger("research_assistant")

SYSTEM_PROMPT = """You are a research synthesis agent. You turn raw search results and
knowledge-base snippets into a clean, honest research report.

Respond with ONLY a JSON object matching this exact shape:
{
  "executive_summary": "2-3 sentence high level answer",
  "key_findings": [
    {"claim": "specific factual claim", "source_url": "https://... or null", "confidence": "high|medium|low"}
  ],
  "detailed_analysis": "a few paragraphs of analysis, grounded only in the provided sources",
  "gaps_and_uncertainties": ["thing the sources don't cover", ...],
  "sources": ["https://...", ...]
}

Hard rules:
- Every claim in key_findings must be traceable to a provided source. If you are not sure, mark confidence "low" and say so in gaps_and_uncertainties instead of stating it as fact.
- Never invent a URL, statistic, date, or name that isn't in the provided sources.
- If sources are empty or thin, say so honestly in gaps_and_uncertainties rather than filling in from general knowledge.
- "sources" must only list URLs that were actually provided to you. When citing knowledge-base content, use the "source" value exactly as given, even if it is not a web URL.
- If LIVE SEARCH RESULTS and KNOWLEDGE BASE snippets conflict on the same fact, trust LIVE SEARCH — it is more current. Note the outdated knowledge-base claim in gaps_and_uncertainties rather than silently dropping it.
- Produce 3-6 key_findings when sources support it. Do not pad with restated or trivial claims just to hit a number.
- If a flagged claim from a previous draft still cannot be backed by a real source, do not invent one to satisfy the critic — remove the claim entirely, or move it to gaps_and_uncertainties. A removed claim is always better than a fabricated fix.
- If a source states a rank, grade, or score in a comparison (e.g. "Company X scored a C"), you must include enough of the comparison for the number to mean what the source means — e.g. whether that was the best, worst, or middle score in the group. A comparative fact stated in isolation, stripped of the context that makes it meaningful, is treated as an unsupported claim even if the number itself is correct.
- Each source below is tagged with its publish date where known. Do not describe a finding as "recent," "latest," or "current" if its source is more than ~6 months old relative to other sources you were given, or if the source itself references being superseded by a newer edition/report. State the actual date or period instead (e.g. "as of a mid-2025 report") so the reader isn't misled about how current the information is.
"""

_USER_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "QUERY: {query}\n\n"
    "LIVE SEARCH RESULTS:\n{search_text}\n\n"
    "KNOWLEDGE BASE (past research):\n{rag_text}\n\n"
    "{issues_block}"
    "Produce the research report as JSON now."
)


def _build_user_prompt(
    query: str,
    search_results: list[dict],
    rag_chunks: list[dict],
    critic_issues: list[str] | None = None,
) -> str:
    search_text = "\n".join(
        f"- [{r['url']}] ({r.get('published_date') or 'date unknown'}) {r['title']}: {r['snippet']}"
        for r in search_results
    ) or "(none found)"
    rag_text = "\n".join(f"- [{c['source']}] {c['content'][:300]}" for c in rag_chunks) or "(no relevant past research)"

    issues_block = ""
    if critic_issues:
        issues_text = "\n".join(f"- {i}" for i in critic_issues)
        issues_block = f"IMPORTANT — a previous draft had these unresolved issues, fix them this time:\n{issues_text}\n\n"

    return _USER_PROMPT_TEMPLATE.format(
        query=query,
        search_text=search_text,
        rag_text=rag_text,
        issues_block=issues_block,
    )


async def run(
    query: str,
    search_results: list[dict],
    rag_chunks: list[dict],
    critic_issues: list[str] | None = None,
) -> ResearchReport:
    try:
        return await generate_json(
            SYSTEM_PROMPT,
            _build_user_prompt(query, search_results, rag_chunks, critic_issues),
            ResearchReport,
        )
    except LLMUnavailableError as exc:
        logger.error(f"synthesizer_agent: generation failed: {exc}")
        # Degrade to an honest, clearly-labeled failure report rather than crashing
        # the WebSocket — the user still gets *something* explaining what happened.
        return ResearchReport(
            executive_summary="Report generation failed — both LLM providers were unavailable.",
            key_findings=[],
            detailed_analysis=f"Error detail: {exc}",
            gaps_and_uncertainties=["No analysis was generated due to an LLM provider outage."],
            sources=[r["url"] for r in search_results],
        )