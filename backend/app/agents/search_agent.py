"""
Search Agent
------------
Job: pull real, live information from the web for the given query.
Grounds the pipeline in reality so the Synthesizer never has to invent facts.

Tavily is primary: it's built for LLM/RAG pipelines (clean snippets, real
SLA) and produces better Synthesizer input. DuckDuckGo (`ddgs`, no API key)
is the fallback for when Tavily is unset or the request fails, so the repo
still runs out of the box with zero config.
"""
import asyncio
import logging
from typing import TypedDict

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from tavily import TavilyClient

from app.config import settings

logger = logging.getLogger("research_assistant")

MAX_RESULTS = 5
_LOW_QUALITY_DOMAINS = {
    "thehonestcoder.com",
    "capfront.net",
}


def _is_low_quality(url: str) -> bool:
    return any(domain in url for domain in _LOW_QUALITY_DOMAINS)

_tavily = TavilyClient(api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None


class SearchResult(TypedDict):
    title: str
    url: str
    snippet: str
    published_date: str 


def _search_tavily_sync(query: str) -> list[SearchResult]:
    raw = _tavily.search(query, max_results=settings.TAVILY_MAX_RESULTS)
    return [
        {
            "title": r.get("title", "").strip(),
            "url": r.get("url", "").strip(),
            "snippet": r.get("content", "").strip(),
            "published_date": (r.get("published_date") or "").strip(),
        }
        for r in raw.get("results", [])
        if r.get("url")
    ]


def _search_duckduckgo_sync(query: str) -> list[SearchResult]:
    with DDGS() as ddgs:
        raw = ddgs.text(query, max_results=MAX_RESULTS)
    return [
        {
            "title": r.get("title", "").strip(),
            "url": r.get("href", "").strip(),
            "snippet": r.get("body", "").strip(),
            "published_date": (r.get("date") or "").strip(),
        }
        for r in raw
        if r.get("href")
    ]


async def run(query: str) -> list[SearchResult]:
    """
    Tries Tavily first (if configured), falls back to DuckDuckGo.
    Both calls run in a thread since neither client is async — blocking
    them inline would freeze the event loop for every other user's
    WebSocket messages while the search is in flight.
    """
    results: list[SearchResult] = []

    if _tavily is not None:
        try:
            results = await asyncio.to_thread(_search_tavily_sync, query)
        except Exception as exc:
            logger.warning(f"search_agent: Tavily failed for '{query}': {exc}")
            results = []

    if not results:
        try:
            results = await asyncio.to_thread(_search_duckduckgo_sync, query)
        except DDGSException as exc:
            logger.warning(f"search_agent: DuckDuckGo fallback failed for '{query}': {exc}")
            results = []

    if not results:
        logger.warning(f"search_agent: no results for '{query}' from any provider")

    filtered = [r for r in results if not _is_low_quality(r["url"])]
    if len(filtered) < len(results):
        logger.info(f"search_agent: dropped {len(results) - len(filtered)} low-quality result(s) for '{query}'")

    return (filtered or results)[:MAX_RESULTS]