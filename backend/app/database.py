from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        # Enable pgvector extension — must exist before any Vector column is created.
        # ankane/pgvector Docker image ships the binary; this just activates it.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Create all tables defined in models.py (users, research_sessions, knowledge_chunks)
        await conn.run_sync(Base.metadata.create_all)

        # HNSW index on knowledge_chunks.embedding for fast cosine similarity search.
        # m=16, ef_construction=64 are standard starting values — good balance of
        # speed vs accuracy for a demo/internship project.
        # IF NOT EXISTS means this is safe to run on every startup.
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS knowledge_chunks_emb_idx
            ON knowledge_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))
