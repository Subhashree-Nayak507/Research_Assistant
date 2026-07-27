from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import settings
from app.database import init_db
from app.routes import auth, research
from app.middleware import RequestLoggingMiddleware
from app.rate_limit import limiter

app = FastAPI(title="AI Research Assistant API", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth.router)
app.include_router(research.router)


@app.on_event("startup")
async def on_startup():
    # Creates pgvector extension + all tables + HNSW index on first run.
    # Safe to call every startup — all statements use IF NOT EXISTS.
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Serve the built React frontend (combined single-service deploy) ──
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Any path that isn't an API route (those were already matched by
        # the routers above, since FastAPI checks routes in order) falls
        # through to here. Always return index.html, not a 404 — this is
        # what makes React Router's client-side paths like /session/abc123
        # work correctly on a real browser refresh, not just in-app clicks.
        return FileResponse(_static_dir / "index.html")