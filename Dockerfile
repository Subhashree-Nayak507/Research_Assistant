# ── Stage 1: build the React frontend into static files ──────────
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
# No VITE_API_BASE/VITE_WS_BASE set here on purpose — api.js falls back to
# this page's own same-origin URL when they're unset in a production build,
# which is correct since this one service serves both frontend and API.
RUN npm run build
# → produces /frontend/dist

# ── Stage 2: the actual backend, now also serving the built frontend ──
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
# Copy the built frontend from stage 1 into a folder the backend will serve
COPY --from=frontend-build /frontend/dist ./static

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}