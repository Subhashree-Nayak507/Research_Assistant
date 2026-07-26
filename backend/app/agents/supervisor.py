"""
Supervisor — LangGraph StateGraph
----------------------------------
Orchestrates the full research pipeline using LangGraph.

Why LangGraph here:
- LangGraph models the pipeline as a directed graph — nodes are agents,
  edges define the flow between them.
- The reflection loop (Synthesizer → Critic → retry if failed) is a
  CONDITIONAL EDGE — impossible to express cleanly in a plain chain.
  LangGraph makes this first-class: should_retry() returns the next node.
- State is a TypedDict shared across all nodes — every agent reads from
  and writes to the same state object. No passing 5 arguments between functions.
- Checkpointing is built-in — if a node crashes, state is preserved.

Pipeline (as a graph):
  search_node → rag_node → synthesize_node → critic_node
                                  ↑                |
                                  |         (if failed + attempts < 2)
                                  └────────────────┘
                                         |
                                  (if passed OR max attempts)
                                         ↓
                                    ingest_node → END

LegalMind used plain Python to understand RAG under the hood.
Here we use LangGraph to orchestrate agents — showing framework-level
thinking on top of that foundation.
"""
import logging
import time
from typing import Callable, Awaitable, Annotated
import operator

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import search_agent, rag_agent, critic_agent, synthesizer_agent
from app.schemas import ResearchReport

logger = logging.getLogger("research_assistant")

ProgressCallback = Callable[[str, str], Awaitable[None]]

MAX_SYNTHESIS_ATTEMPTS = 2


# ── Shared State ────────────────────────────────────────────────────────────────
# Every node reads from and writes to this TypedDict.
# This is the core LangGraph concept — shared state replaces function arguments.
# Annotated[list, operator.add] means lists are APPENDED not overwritten
# when multiple nodes write to the same key.

class ResearchState(TypedDict):
    # Inputs — set before graph starts
    query: str
    user_id: str
    session_id: str
    db: AsyncSession
    on_progress: ProgressCallback

    # Agent outputs — filled as pipeline runs
    search_results: list          # from search_node
    rag_chunks: list              # from rag_node
    report: ResearchReport | None # from synthesize_node
    critic_issues: list[str]      # from critic_node — empty = passed
    attempt: int                  # tracks retry count for reflection loop

    # Timing — each node records its own duration
    timings: Annotated[dict, lambda a, b: {**a, **b}]


# ── Node helpers ────────────────────────────────────────────────────────────────

def _now() -> float:
    return time.perf_counter()

def _elapsed(t0: float) -> float:
    return round(time.perf_counter() - t0, 3)


# ── Nodes ───────────────────────────────────────────────────────────────────────
# Each node is an async function that:
#   1. Reads what it needs from state
#   2. Does its job
#   3. Returns a dict of ONLY the keys it changed
# LangGraph merges the returned dict into the full state automatically.

async def search_node(state: ResearchState) -> dict:
    """
    Node 1: Search Agent
    Calls DuckDuckGo for live web results grounded in reality.
    """
    await state["on_progress"]("search", "Searching latest sources...")
    t0 = _now()
    results = await search_agent.run(state["query"])
    return {
        "search_results": results,
        "timings": {"search_agent": _elapsed(t0)},
    }


async def rag_node(state: ResearchState) -> dict:
    """
    Node 2: RAG Agent (retrieve)
    LangChain PGVector retriever — pulls closest chunks from past research.
    """
    await state["on_progress"]("rag", "Checking knowledge base...")
    t0 = _now()
    chunks = await rag_agent.run(state["query"], state["user_id"], state["db"])
    return {
        "rag_chunks": chunks,
        "timings": {"rag_agent": _elapsed(t0)},
    }


async def synthesize_node(state: ResearchState) -> dict:
    """
    Node 3: Synthesizer Agent
    Calls Groq → Gemini fallback. Returns structured ResearchReport.
    On retry pass, critic_issues are passed in so Synthesizer can fix them.
    """
    attempt = state.get("attempt", 0) + 1
    msg = "Writing your report..." if attempt == 1 else "Revising based on verification feedback..."
    await state["on_progress"]("synthesize", msg)

    t0 = _now()
    # critic_issues is empty list on first attempt, populated on retry
    issues = state.get("critic_issues", []) or None
    report = await synthesizer_agent.run(
        state["query"],
        state["search_results"],
        state["rag_chunks"],
        issues,
    )
    return {
        "report": report,
        "attempt": attempt,
        "timings": {"synthesizer_agent": _elapsed(t0)},
    }


async def critic_node(state: ResearchState) -> dict:
    """
    Node 4: Critic Agent — Reflection Pattern
    Checks every claim in the report against sources.
    Returns issues list — empty means passed.
    This is what makes "agent never hallucinates" a real claim.
    """
    await state["on_progress"]("critic", "Critic verifying quality...")
    t0 = _now()

    report = state["report"]
    draft_findings = [
        {"claim": f.claim, "source_url": f.source_url}
        for f in report.key_findings
    ]
    all_sources = state["search_results"] + [
        {"url": c["source"], "snippet": c["content"]}
        for c in state["rag_chunks"]
    ]
    verdict = await critic_agent.run(draft_findings, all_sources)

    # If failed and out of retries — surface issues honestly in report
    if not verdict["passed"] and state.get("attempt", 1) >= MAX_SYNTHESIS_ATTEMPTS:
        report.gaps_and_uncertainties = list(report.gaps_and_uncertainties) + [
            f"Unverified after {MAX_SYNTHESIS_ATTEMPTS} passes: {issue}"
            for issue in verdict["issues"]
        ]
        logger.info(f"supervisor: critic failed after max attempts, surfacing issues")

    if not verdict["passed"]:
        logger.info(f"supervisor: critic rejected attempt {state.get('attempt')}: {verdict['issues']}")

    return {
        "critic_issues": verdict["issues"] if not verdict["passed"] else [],
        "report": report,
        "timings": {"critic_agent": _elapsed(t0)},
    }


async def ingest_node(state: ResearchState) -> dict:
    """
    Node 5: RAG Agent (ingest)
    Stores finished report in PGVector so future queries have memory.
    Failure here does NOT fail the request — ingestion is best-effort.
    """
    await state["on_progress"]("ingest", "Saving to knowledge base...")
    t0 = _now()
    try:
        await rag_agent.ingest(
            state["db"],
            state["user_id"],
            state["session_id"],
            state["query"],
            state["report"],
        )
    except Exception:
        logger.exception("supervisor: rag ingestion failed, continuing")
    return {"timings": {"rag_ingest": _elapsed(t0)}}


# ── Conditional Edge ─────────────────────────────────────────────────────────────
# This is the Reflection Loop — the key reason we use LangGraph.
# A plain chain cannot loop back. LangGraph conditional edges make this clean.

def should_retry(state: ResearchState) -> str:
    """
    After Critic runs — decide next node:
    - If critic passed → go to ingest
    - If critic failed AND attempts remaining → retry synthesize
    - If critic failed AND no attempts left → go to ingest anyway (issues surfaced in report)
    """
    issues = state.get("critic_issues", [])
    attempt = state.get("attempt", 1)

    if not issues:
        # Critic passed — move to ingest
        return "ingest"
    if attempt < MAX_SYNTHESIS_ATTEMPTS:
        # Critic failed, still have attempts — loop back to synthesizer
        return "synthesize"
    # Out of attempts — ship with issues marked in gaps_and_uncertainties
    return "ingest"


# ── Build the Graph ──────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    """
    Defines the LangGraph StateGraph:
    - Nodes: each agent function
    - Edges: fixed flow except after critic (conditional)
    - Entry point: search_node
    """
    graph = StateGraph(ResearchState)

    # Add nodes — each is an async function
    graph.add_node("search", search_node)
    graph.add_node("rag", rag_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("critic", critic_node)
    graph.add_node("ingest", ingest_node)

    # Fixed edges — always go in this direction
    graph.set_entry_point("search")
    graph.add_edge("search", "rag")
    graph.add_edge("rag", "synthesize")
    graph.add_edge("synthesize", "critic")

    # Conditional edge — Reflection Loop
    # After critic runs, should_retry() decides: "synthesize" or "ingest"
    graph.add_conditional_edges(
        "critic",           # from this node
        should_retry,       # call this function to decide
        {
            "synthesize": "synthesize",  # loop back if failed
            "ingest": "ingest",          # proceed if passed
        },
    )

    graph.add_edge("ingest", END)

    return graph.compile()


# Compile once at module load — reused for every request
_graph = _build_graph()


# ── Public Entry Point ───────────────────────────────────────────────────────────

async def run_pipeline(
    query: str,
    user_id: str,
    session_id: str,
    db: AsyncSession,
    on_progress: ProgressCallback,
) -> tuple[ResearchReport, dict]:
    """
    Called by routes/research.py WebSocket handler.
    Initializes LangGraph state and runs the compiled graph.
    Returns (report, timing_dict) — same interface as before.
    """
    # Initial state — nodes will fill in the rest
    initial_state: ResearchState = {
        "query": query,
        "user_id": user_id,
        "session_id": session_id,
        "db": db,
        "on_progress": on_progress,
        "search_results": [],
        "rag_chunks": [],
        "report": None,
        "critic_issues": [],
        "attempt": 0,
        "timings": {},
    }

    start = time.perf_counter()

    # Run the LangGraph — streams through all nodes automatically
    final_state = await _graph.ainvoke(initial_state)

    await on_progress("done", "Report ready.")

    total = round(time.perf_counter() - start, 3)
    timing = {**final_state["timings"], "total_seconds": total}

    return final_state["report"], timing