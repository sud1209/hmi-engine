"""
Auth middleware — JWT bearer tokens + static API key for ingest.

Environment variables:
  SECRET_KEY      HMAC secret for signing JWTs (required in prod; dev default used if absent)
  API_KEY_HASH    SHA-256 hex of the ingest API key (optional; set to restrict /ingest/kpis)

Public endpoints (no auth required):
  GET  /health
  GET  /dashboard
  GET  /sse
  GET  /tools/list
  GET  /history
  GET  /msa
  POST /query
  GET  /metrics

Protected endpoints:
  POST /tools/call/*   — Bearer JWT
  POST /ingest/kpis    — Bearer JWT  OR  X-API-Key matching API_KEY_HASH
"""
import hashlib
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from jose import JWTError, jwt as jose_jwt
    _JOSE_AVAILABLE = True
except ImportError:
    _JOSE_AVAILABLE = False

SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
API_KEY_HASH: str = os.getenv("API_KEY_HASH", "")

_bearer = HTTPBearer(auto_error=False)

# Paths that require no authentication.
# Read-only market data endpoints (/history, /msa, /query) are intentionally
# public — they power the dashboard and NL query features for unauthenticated users.
# Write and tool-call endpoints (/tools/call/*, /ingest/kpis) require Bearer JWT.
_PUBLIC_PREFIXES = (
    "/health",
    "/dashboard",
    "/sse",
    "/tools/list",
    "/docs",
    "/openapi",
    "/history",   # read-only market history — public
    "/msa",       # read-only MSA rankings — public
    "/query",     # NL query over public data — public (rate-limited separately)
    "/metrics",   # Prometheus scrape endpoint
)


def _is_public(path: str) -> bool:
    """Return True if the path requires no authentication."""
    for p in _PUBLIC_PREFIXES:
        if path == p or path.startswith(p + "/") or path.startswith(p + "?"):
            return True
    return False


def _verify_jwt(token: str) -> dict:
    if not _JOSE_AVAILABLE:
        # python-jose not installed — skip JWT validation in dev
        return {"sub": "dev"}
    try:
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _verify_api_key(key: str) -> bool:
    if not API_KEY_HASH:
        return False
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key_hash == API_KEY_HASH


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """FastAPI dependency — validates Bearer JWT or API key."""
    if _is_public(request.url.path):
        return {}

    # Try API-key header first (for /ingest/kpis from pipeline)
    api_key = request.headers.get("X-API-Key", "")
    if api_key and _verify_api_key(api_key):
        return {"sub": "api-key"}

    # Fall back to Bearer JWT
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _verify_jwt(credentials.credentials)
