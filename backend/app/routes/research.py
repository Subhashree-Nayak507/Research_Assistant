import json
import logging
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, ResearchSession
from app.schemas import ResearchSessionOut
from app.auth import get_current_user, COOKIE_NAME
from app.agents.supervisor import run_pipeline
from app.config import settings
from app.schemas import ResearchSessionOut, KnowledgeChunkOut
from app.agents import rag_agent
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect


router = APIRouter(prefix="/research", tags=["research"])
logger = logging.getLogger("research_assistant")


@router.get("/history", response_model=list[ResearchSessionOut])
async def history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.user_id == user.id).order_by(ResearchSession.created_at.desc())
    )
    return result.scalars().all()


async def _authenticate_ws(websocket: WebSocket, db: AsyncSession) -> User | None:
    # Browsers automatically attach cookies to the WebSocket handshake for
    # same-site/CORS-allowed origins, so no token needs to travel in the URL.
    token = websocket.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# --- Basic per-user rate limiting for research queries ---
# Research queries hit LLM APIs (real money/quota), so they get a tighter
# limit than plain REST calls. This is a simple in-memory sliding window —
# fine for a single-process demo. For multiple backend workers/replicas,
# swap this dict for Redis (INCR + EXPIRE, or a sorted set) so all workers
# share the same counters.
RESEARCH_RATE_LIMIT = 5          # max queries
RESEARCH_RATE_WINDOW = 600       # per 10 minutes (seconds)
_query_log: dict[str, deque] = defaultdict(deque)


def _is_rate_limited(user_id: str) -> bool:
    now = time.time()
    log = _query_log[user_id]
    while log and now - log[0] > RESEARCH_RATE_WINDOW:
        log.popleft()
    if len(log) >= RESEARCH_RATE_LIMIT:
        return True
    log.append(now)
    return False


@router.websocket("/ws")
async def research_ws(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """
    Basic token auth over WebSocket: the JWT rides in the httpOnly
    `access_token` cookie set by /auth/login, same as REST calls.

    Streams live progress events, then the final structured report with
    per-agent timing:
      {"stage": "search", "message": "Searching latest sources..."}
      ...
      {"stage": "report", "report": {...}, "timing": {...}}
    """
    user = await _authenticate_ws(websocket, db)
    if not user:
        await websocket.close(code=4401)  # custom code: unauthorized
        return

    user_id = user.id  

    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw) # raw string sned by browser here i converted to python dict.
            query = data.get("query", "").strip()

            if not query:
                await websocket.send_json({"stage": "error", "message": "Empty query."})
                continue # wait for next messgae without closing connection.

            if _is_rate_limited(user_id):
                logger.warning(f"rate limit hit: user={user_id}")
                await websocket.send_json({
                    "stage": "error",
                    "message": f"Rate limit reached: {RESEARCH_RATE_LIMIT} queries per "
                               f"{RESEARCH_RATE_WINDOW // 60} minutes. Try again shortly.",
                })
                continue

            session = ResearchSession(user_id=user_id, query=query, status="running")
            db.add(session)
            await db.commit()
            await db.refresh(session)
            session_id = session.id

            async def on_progress(stage: str, message: str):
                await websocket.send_json({"stage": stage, "message": message})

            request_start = time.perf_counter()
            try:
                report, timing = await run_pipeline(query, user_id, session_id, db, on_progress)
                session.status = "done"
                session.report_json = report.model_dump_json()
                await db.commit()

                logger.info(
                    f"research done: user={user_id} session={session_id} "
                    f"total={timing['total_seconds']}s breakdown={timing}"
                )
                await websocket.send_json({
                    "stage": "report",
                    "report": report.model_dump(),
                    "timing": timing,
                })
            except Exception as exc: 
                session.status = "failed"
                await db.commit()
                elapsed = round(time.perf_counter() - request_start, 3)
                logger.exception(f"research failed: user={user_id} session={session_id} after={elapsed}s")
                await websocket.send_json({"stage": "error", "message": str(exc)})

    except WebSocketDisconnect:
        pass

@router.get("/knowledge", response_model=list[KnowledgeChunkOut])
async def list_knowledge(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await rag_agent.list_chunks(db, user.id)


