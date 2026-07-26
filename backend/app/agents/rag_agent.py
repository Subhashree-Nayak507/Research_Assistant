"""
RAG Agent
---------
Talks directly to our own KnowledgeChunk table through the AsyncSession
FastAPI already hands us, using pgvector's cosine_distance() comparator.
Reuses the app's pooled async engine, and gives us a real row to
dedup/update/delete against — fixing pooling, dedup, staleness, and
delete all from the same root fix.
"""
import hashlib
import logging
from datetime import datetime
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_client import embed_text, LLMUnavailableError
from app.models import KnowledgeChunk

logger = logging.getLogger("research_assistant")

SIMILARITY_THRESHOLD = 0.35


class RagChunk(TypedDict):
    content: str
    source: str
    score: float


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


async def run(query: str, user_id: str, db: AsyncSession, top_k: int = 5) -> list[RagChunk]:
    try:
        query_embedding = await embed_text(query, task_type="retrieval_query")
    except LLMUnavailableError as exc:
        logger.warning(f"rag_agent: embedding failed for query={query!r}: {exc}")
        return []

    distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(KnowledgeChunk, distance.label("distance"))
        .where(KnowledgeChunk.user_id == user_id)
        .where(distance < SIMILARITY_THRESHOLD)
        .order_by(distance)
        .limit(top_k)
    )

    try:
        result = await db.execute(stmt)
        rows = result.all()
    except Exception:
        logger.exception(f"rag_agent: retrieval failed for query={query!r}")
        return []

    chunks: list[RagChunk] = [
        {"content": chunk.content, "source": chunk.source or "", "score": round(float(dist), 4)}
        for chunk, dist in rows
    ]
    logger.info(f"rag_agent: retrieved {len(chunks)} chunks above threshold for query={query!r}")
    return chunks


async def ingest(db: AsyncSession, user_id: str, session_id: str, query: str, report) -> None:
    pieces: list[tuple[str, str]] = [(report.executive_summary, query)]
    for finding in report.key_findings:
        pieces.append((finding.claim, finding.source_url or query))

    inserted = 0
    refreshed = 0

    for content, source in pieces:
        content = (content or "").strip()
        if not content:
            continue
        content_hash = _hash_content(content)

        try:
            embedding = await embed_text(content, task_type="retrieval_document")
        except LLMUnavailableError as exc:
            logger.warning(f"rag_agent.ingest: embedding failed, skipping chunk: {exc}")
            continue

        try:
            existing = await db.execute(
                select(KnowledgeChunk).where(
                    KnowledgeChunk.user_id == user_id,
                    KnowledgeChunk.content_hash == content_hash,
                )
            )
            row = existing.scalar_one_or_none()

            if row:
                row.embedding = embedding
                row.source = source
                row.session_id = session_id
                row.updated_at = datetime.utcnow()
                refreshed += 1
            else:
                db.add(KnowledgeChunk(
                    user_id=user_id,
                    session_id=session_id,
                    content=content,
                    content_hash=content_hash,
                    source=source,
                    embedding=embedding,
                    updated_at=datetime.utcnow(),
                ))
                inserted += 1
            await db.flush()
        except Exception as exc:
            await db.rollback()
            logger.warning(f"rag_agent.ingest: skipping chunk after DB error: {exc}")
            continue

    try:
        await db.commit()
        logger.info(f"rag_agent: ingested {inserted} new / {refreshed} refreshed chunks for user={user_id}")
    except Exception:
        await db.rollback()
        logger.exception("rag_agent.ingest: failed to store chunks")


async def list_chunks(db: AsyncSession, user_id: str) -> list[KnowledgeChunk]:
    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.user_id == user_id)
        .order_by(KnowledgeChunk.updated_at.desc())
    )
    return list(result.scalars().all())