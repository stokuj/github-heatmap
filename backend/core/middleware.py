from collections import defaultdict
from collections import deque
from collections.abc import Awaitable
from collections.abc import Callable
from threading import RLock
from time import monotonic

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class HeatmapRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter for GET /heatmap/me requests."""

    def __init__(
        self, app, requests_per_window: int = 30, window_seconds: int = 60
    ) -> None:
        super().__init__(app)
        # Guard against invalid config values (0 or negatives).
        self.max_requests = max(1, requests_per_window)
        self.window_seconds = max(1, window_seconds)
        # In-memory storage: one queue of timestamps per client key.
        self._ip_buckets: dict[str, deque[float]] = defaultdict(deque)
        # Lock keeps operations on shared buckets thread-safe.
        self._lock = RLock()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 1) Limit only the expensive endpoint. Everything else passes through.
        if request.method != "GET" or request.url.path != "/heatmap/me":
            return await call_next(request)

        ip = self._client_ip(request)
        now = monotonic()

        with self._lock:
            # 2) Get current client bucket and evict timestamps outside the window.
            bucket = self._ip_buckets[ip]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            # 3) If limit reached, return 429 with Retry-After.
            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests"},
                    headers={"Retry-After": str(retry_after)},
                )

            # 4) Count current request and continue to endpoint handler.
            bucket.append(now)

        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Cloud Run and reverse proxies usually set X-Forwarded-For.
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip() or "unknown"

        if request.client and request.client.host:
            return request.client.host

        return "unknown"
