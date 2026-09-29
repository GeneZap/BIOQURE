"""Reject oversized request bodies early (multipart / JSON)."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)
        cl = request.headers.get("content-length")
        if cl:
            try:
                n = int(cl)
            except ValueError:
                return await call_next(request)
            if n > self.max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": (
                            f"Request body too large (>{self.max_bytes // (1024 * 1024)} MiB). "
                            "Increase GENEZAP_MAX_UPLOAD_MB if your host allows."
                        )
                    },
                )
        return await call_next(request)
