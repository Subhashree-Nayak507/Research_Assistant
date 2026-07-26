"""
Critic Agent (Reflection Pattern)
----------------------------------
Job: check the draft findings against the retrieved sources before anything
reaches the user. This is the piece that makes "agent never hallucinates" a
real claim instead of marketing copy.

Checks it makes the LLM justify:
- Is every claim traceable to one of the provided sources?
- Is anything asserted that the sources don't actually support?
- Should any claim's confidence be downgraded?

If `passed` is False, the Supervisor loops back with the issues so the
Synthesizer can revise instead of shipping an unverified report.
"""
import logging
from typing import TypedDict

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from app.agents.llm_client import generate_json, LLMUnavailableError

logger = logging.getLogger("research_assistant")


class CriticVerdict(TypedDict):
    passed: bool
    issues: list[str]


class _CriticResponse(BaseModel):
    passed: bool = Field(description="True only if every claim is backed by a source")
    issues: list[str] = Field(default_factory=list, description="Specific unsupported or dubious claims")


SYSTEM_PROMPT = """You are a strict fact-checking critic for a research pipeline.
You receive draft findings and the source snippets they are supposed to be based on.
Your only job: catch claims that are NOT actually supported by the sources.

Respond with ONLY a JSON object matching this shape, nothing else:
{"passed": true|false, "issues": ["specific unsupported claim 1", ...]}

Rules:
- "passed" is true only if every finding is clearly backed by at least one source.
- If sources list is empty, passed must be false (nothing to ground the claims in).
- Be specific in "issues" — name the exact claim, not a vague complaint.
- Do not invent issues that aren't there. If everything is well-grounded, passed=true and issues=[].
- Pay special attention to numbers, dates, and statistics — a claim citing a different figure than what the source actually states counts as unsupported, even if the general topic matches.
- A claim that is partially correct but has an unsupported detail (e.g. correct event, wrong number) still counts as an issue — name the specific detail that's wrong, not the whole claim.
- Do not flag grammar, writing style, tone, or structure — only factual grounding. A claim can be poorly written and still pass if it's supported.
- A comparative fact (a grade, rank, score, or standing) stated without the context needed to know whether it's good or bad relative to the group is an issue, even if the number matches the source exactly. Example: a source says a company scored a "C" and that this was the highest score among six companies graded D+ or lower; a finding that only says "the company received a C grade" — with no top/bottom framing — misrepresents the source and must be flagged.
- If a finding calls something "recent," "latest," or "current" but its cited source is visibly older than other sources in this batch, or the source itself indicates a newer edition/report exists, flag it as a staleness issue and name the actual date if given."""


# Same PromptTemplate pattern as synthesizer_agent.py — a fill-in-the-blanks
# template instead of manual f-string concatenation.
_USER_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "DRAFT FINDINGS:\n{findings_text}\n\n"
    "AVAILABLE SOURCES:\n{sources_text}\n\n"
    "Check each finding against the sources and return your verdict as JSON."
)


def _build_user_prompt(draft_findings: list[dict], sources: list[dict]) -> str:
    findings_text = "\n".join(f"- {f['claim']} (cited source: {f.get('source_url', 'none')})" for f in draft_findings)
    sources_text = "\n".join(
        f"- [{s['url']}] ({s.get('published_date') or 'date unknown'}) {s.get('snippet', '')[:300]}"
        for s in sources
    ) or "(no sources found)"
    return _USER_PROMPT_TEMPLATE.format(
        findings_text=findings_text or "(no findings)",
        sources_text=sources_text,
    )


async def run(draft_findings: list[dict], sources: list[dict]) -> CriticVerdict:
    if not draft_findings:
        return {"passed": False, "issues": ["No findings were produced to verify."]}

    try:
        result = await generate_json(
            SYSTEM_PROMPT,
            _build_user_prompt(draft_findings, sources),
            _CriticResponse,
        )
        return {"passed": result.passed, "issues": result.issues}
    except LLMUnavailableError as exc:
        # Fail safe: if we can't verify, don't silently claim success.
        logger.error(f"critic_agent: verification unavailable: {exc}")
        return {"passed": False, "issues": [f"Could not run verification: {exc}"]}