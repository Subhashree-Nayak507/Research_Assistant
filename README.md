# 🧠 AI Research Assistant — Multi-Agent RAG System

> A production-ready multi-agent AI research platform that combines live web search, Retrieval-Augmented Generation (RAG), reflection-based fact checking, and real-time streaming to generate reliable, source-backed research reports.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![React](https://img.shields.io/badge/React-Vite-61DAFB)

---

# ✨ Features

- 🤖 Multi-Agent Architecture using **LangGraph StateGraph**
- 🌐 Live Web Search (Tavily + DuckDuckGo fallback)
- 🧠 RAG Memory using **PostgreSQL + pgvector**
- 🔄 Reflection Loop for automatic fact verification
- 📄 Structured research reports with confidence scores
- ⚡ Real-time progress updates via WebSockets
- 🔐 JWT Authentication using httpOnly Cookies
- 🚦 WebSocket & REST API Rate Limiting
- 🐳 Fully Dockerized deployment
- 📊 Async FastAPI backend with SQLAlchemy

---

# 🏗️ Tech Stack

| Category | Technology |
|-----------|------------|
| Backend | FastAPI, Python |
| Agent Framework | LangGraph StateGraph |
| LLM | Groq (Primary), Gemini (Fallback) |
| Search | Tavily API, DuckDuckGo |
| Database | PostgreSQL + pgvector |
| ORM | SQLAlchemy Async |
| Frontend | React + Vite |
| Streaming | WebSockets |
| Authentication | JWT (httpOnly Cookies) |
| Validation | Pydantic |
| Deployment | Docker Compose |

---

# 🚀 How It Works

When a user asks a research question, the system executes a coordinated multi-agent workflow.

```text
User Query
     │
     ▼
Search Agent
     │
     ▼
Retrieve Previous Research (RAG)
     │
     ▼
Synthesizer Agent
     │
     ▼
Critic Agent
     │
     ├───────────────┐
     │               │
     │ Failed        │ Passed
     ▼               ▼
Rewrite         Store Report
     │               │
     └──────► Return Result
```

Throughout the process, progress is streamed live to the frontend:

```
Searching...
↓
Checking Memory...
↓
Writing Report...
↓
Verifying Facts...
↓
Completed
```

---

# 🧩 System Architecture

```text
React Frontend
       │
       │ WebSocket
       ▼
FastAPI Backend
       │
       ▼
LangGraph StateGraph
       │
       ├── Search Agent
       │      ├── Tavily
       │      └── DuckDuckGo (Fallback)
       │
       ├── RAG Agent
       │      └── PostgreSQL + pgvector
       │
       ├── Synthesizer Agent
       │      └── Groq → Gemini Fallback
       │
       ├── Critic Agent
       │      └── Reflection & Fact Verification
       │
       └── Ingestion Agent
              └── Stores verified knowledge
```

---

# 🤖 Multi-Agent Workflow

## 🔎 Search Agent

- Searches live web sources
- Tavily as the primary search provider
- Automatically falls back to DuckDuckGo
- Filters known low-quality domains

---

## 📚 RAG Agent

Retrieves relevant previous research using semantic search.

- PostgreSQL
- pgvector
- Cosine similarity search
- User-specific memory isolation
- Content hash deduplication

---

## ✍️ Synthesizer Agent

Combines:

- Live web search
- Previous research
- User query

Generates a structured research report with:

- Executive Summary
- Key Findings
- Detailed Analysis
- References
- Confidence Scores

Structured output is validated using **Pydantic**.

---

## ✅ Critic Agent

Instead of trusting the first AI response, a second independent LLM verifies every key finding.

Checks include:

- Unsupported claims
- Incorrect statistics
- Wrong dates
- Missing context
- Stale information
- Hallucinated facts

If verification fails, the report is automatically rewritten.

Maximum retries: **2**

---

## 💾 Ingestion Agent

Verified reports are embedded and stored for future retrieval.

Features:

- Embedding generation
- Content hash deduplication
- Per-user storage
- Semantic indexing with pgvector

---

# 🔁 Reflection Loop

Unlike a linear AI pipeline, this project uses a reflection-based workflow.

```text
Generate Report
       │
       ▼
Critic Review
       │
 ┌─────┴──────┐
 │            │
Pass       Fail
 │            │
 ▼            ▼
Store      Rewrite
              │
              ▼
         Critic Review
```

This significantly reduces hallucinations by forcing the model to verify its own work before returning results.

---

# 📦 Shared LangGraph State

Each agent reads from and writes to a shared state.

```python
class ResearchState(TypedDict):
    query: str
    user_id: str
    session_id: str
    db: AsyncSession

    search_results: list
    rag_chunks: list
    report: ResearchReport
    critic_issues: list[str]
    attempt: int
    timings: dict
```

---

# 🗄️ Database

The project uses **raw SQLAlchemy with pgvector** instead of external vector database wrappers.

Benefits:

- Async SQLAlchemy sessions
- Native PostgreSQL queries
- pgvector cosine similarity
- User-level filtering
- Content deduplication
- Single database connection pool

---

# 🔒 Authentication

- JWT Authentication
- httpOnly Cookies
- Authorization Header support
- Protected API routes
- Secure token handling

---

# 🚦 Rate Limiting

Two independent strategies are used.

### REST APIs

- slowapi
- IP-based protection
- Prevents brute-force attacks

### WebSocket

Custom sliding-window limiter

- User-based
- Counts individual research requests
- Prevents abuse over persistent WebSocket connections

---

# ⚙️ LLM Strategy

```
Groq
   │
Available?
   │
 ┌─┴──┐
 │Yes │
 └─┬──┘
   │
Return
   │
   ▼
No
   │
   ▼
Gemini
```

All LLM outputs are validated with **Pydantic** before entering the application.

---

# 🚀 Running Locally

## Clone Repository

```bash
git clone https://github.com/Subhashree-Nayak507/Research_Assistant.git

cd AI_Research_Assistant
```

## Configure Environment

```bash
cp .env.example .env

cp backend/.env.example backend/.env
```

Update the environment variables with your API keys.

---

## Start the Project

```bash
docker compose up --build
```

---

# 🌍 Application URLs

| Service | URL |
|----------|-----|
| Frontend | http://localhost:5174 |
| Backend | http://localhost:8001 |
| Swagger Docs | http://localhost:8001/docs |

---

# 🔑 Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Primary LLM |
| `GEMINI_API_KEY` | Fallback LLM & Embeddings |
| `TAVILY_API_KEY` | Web Search |
| `JWT_SECRET_KEY` | JWT Authentication |
| `POSTGRES_USER` | PostgreSQL User |
| `POSTGRES_PASSWORD` | PostgreSQL Password |
| `POSTGRES_DB` | PostgreSQL Database |

---

# 📂 Project Highlights

- Multi-Agent AI Architecture
- Reflection-based Self Verification
- Production-grade RAG Pipeline
- LangGraph State Management
- Real-time WebSocket Streaming
- PostgreSQL + pgvector Semantic Search
- Async FastAPI Backend
- Dockerized Deployment
- Secure Authentication
- Automatic LLM Fallback
- Pydantic Structured Outputs

---

# ⚠️ Current Limitations

- Only `key_findings` are independently verified.
- Search quality filtering uses a manually maintained blocklist.
- WebSocket rate limiter is in-memory; Redis is recommended for multi-instance deployments.

---

# 🔮 Future Improvements

- Redis-based distributed rate limiting
- Citation-level verification
- Multi-document research mode
- PDF & DOCX report export
- Research history dashboard
- Source reliability scoring
- Multi-language support
- Human feedback loop
- Agent performance analytics

