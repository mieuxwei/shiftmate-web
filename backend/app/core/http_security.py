import json
import logging
import re
import threading
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from backend.app.core.quotas import QuotaExceededError

logger = logging.getLogger("shiftmate.http")
SAFE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


class FixedWindowRateLimiter:
    """Bounded process-local limiter for the configured max-one Cloud Run instance."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int]:
        timestamp = time.monotonic() if now is None else now
        cutoff = timestamp - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(events[0] + self.window_seconds - timestamp))
                return False, retry_after
            events.append(timestamp)
            if len(self._events) > 4096:
                self._events = defaultdict(
                    deque,
                    {item: values for item, values in self._events.items() if values},
                )
            return True, 0


def build_http_guard(
    limiter: FixedWindowRateLimiter,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    async def guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = _request_id(request.headers.get("x-request-id"))
        started = time.monotonic()
        path = request.url.path
        if _rate_limited_path(path):
            peer = request.client.host if request.client else "unknown"
            allowed, retry_after = limiter.allow(peer)
            if not allowed:
                rate_response = JSONResponse(
                    {"detail": "RATE_LIMIT_EXCEEDED", "request_id": request_id},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
                _log_request(request, rate_response.status_code, request_id, started)
                return rate_response
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(
                {"detail": "INTERNAL_ERROR", "request_id": request_id},
                status_code=500,
            )
            logger.error(
                json.dumps(
                    {
                        "event": "unhandled_request_error",
                        "method": request.method,
                        "path": _safe_path(path),
                        "request_id": request_id,
                    },
                    sort_keys=True,
                )
            )
        response.headers["X-Request-ID"] = request_id
        _log_request(request, response.status_code, request_id, started)
        return response

    return guard


def safe_http_error(_: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, HTTPException):
        return JSONResponse({"detail": "INTERNAL_ERROR"}, status_code=500)
    detail = error.detail
    code = detail if isinstance(detail, str) and SAFE_CODE.fullmatch(detail) else None
    if code is None:
        code = {
            400: "INVALID_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            422: "INVALID_REQUEST",
            429: "RATE_LIMIT_EXCEEDED",
            503: "SERVICE_UNAVAILABLE",
        }.get(error.status_code, "REQUEST_FAILED")
    return JSONResponse(
        {"detail": code}, status_code=error.status_code, headers=error.headers
    )


def safe_validation_error(_: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, RequestValidationError):
        return JSONResponse({"detail": "INTERNAL_ERROR"}, status_code=500)
    return JSONResponse({"detail": "VALIDATION_ERROR"}, status_code=422)


def quota_exceeded_error(_: Request, error: Exception) -> JSONResponse:
    code = (
        error.code if isinstance(error, QuotaExceededError) else "RATE_LIMIT_EXCEEDED"
    )
    return JSONResponse(
        {"detail": code}, status_code=429, headers={"Retry-After": "86400"}
    )


def _rate_limited_path(path: str) -> bool:
    return (
        path.startswith("/api/v1/") and path != "/api/v1/health"
    ) or path.startswith("/mcp")


def _request_id(candidate: str | None) -> str:
    if candidate and re.fullmatch(r"[A-Za-z0-9_-]{8,64}", candidate):
        return candidate
    return uuid4().hex


def _log_request(
    request: Request, status_code: int, request_id: str, started: float
) -> None:
    logger.info(
        json.dumps(
            {
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
                "event": "http_request",
                "method": request.method,
                "path": _safe_path(request.url.path),
                "request_id": request_id,
                "status": status_code,
            },
            sort_keys=True,
        )
    )


def _safe_path(path: str) -> str:
    return re.sub(
        r"(?i)[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
        r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        "{id}",
        path,
    )
