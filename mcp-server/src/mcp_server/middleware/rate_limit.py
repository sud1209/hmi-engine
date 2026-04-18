"""
Rate limiting via slowapi (Starlette-compatible wrapper around limits).

Limits:
  GET  /dashboard          → 60 / minute / IP
  POST /tools/call/*       → 20 / minute / IP
  POST /ingest/kpis        → 10 / minute / IP
  POST /query              → 10 / minute / IP

Usage — attach to FastAPI app in main.py:
  from .middleware.rate_limit import limiter, rate_limit_handler
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


def _get_client_ip(request: Request) -> str:
    """Return the real client IP.

    When behind Caddy, Caddy appends the real client IP as the rightmost
    value in X-Forwarded-For. We use rightmost to prevent clients from
    spoofing the leftmost position to bypass rate limiting.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Caddy appends the real client IP as rightmost — use it to prevent spoofing
        return forwarded_for.split(",")[-1].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_get_client_ip)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. Please try again later."},
    )
