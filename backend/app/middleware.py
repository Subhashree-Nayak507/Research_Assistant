import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("research_assistant")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request: a request id, method, path, status code, and
    duration in milliseconds. This is the "basics" layer — enough to debug
    issues and see which endpoints are slow. Swap `logger` for a JSON
    formatter + shipping to a log aggregator (e.g. Loki, CloudWatch) later.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        logger.info(f"[{request_id}] --> {request.method} {request.url.path}")

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(f"[{request_id}] <-- FAILED after {duration_ms:.1f}ms")
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"[{request_id}] <-- {response.status_code} {request.method} "
            f"{request.url.path} ({duration_ms:.1f}ms)"
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        return response
