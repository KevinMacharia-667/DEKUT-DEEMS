"""
In-memory sliding window rate limiter for security-sensitive auth endpoints.
Thread-safe, zero external dependencies, and configurable via .env.
"""

from collections import defaultdict
import math
from threading import Lock
import time

from fastapi import HTTPException, Request, status

from app.config import get_settings


class SlidingWindowRateLimiter:
    """
    Sliding window log rate limiter.
    Stores request timestamps per (client_ip, endpoint_key).
    """

    def __init__(self):
        self._lock = Lock()
        self._history: dict[tuple[str, str], list[float]] = defaultdict(list)

    def check(self, ip: str, endpoint: str, max_attempts: int, window_seconds: int):
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Filter out timestamps older than the sliding window
            timestamps = [t for t in self._history[(ip, endpoint)] if t > cutoff]
            if len(timestamps) >= max_attempts:
                # Estimate retry-after in seconds until the oldest attempt leaves the window
                oldest_in_window = timestamps[0]
                retry_after = max(1, int(math.ceil(window_seconds - (now - oldest_in_window))))
                self._history[(ip, endpoint)] = timestamps
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Too many attempts. Maximum allowed is {max_attempts} attempt(s) per "
                        f"{window_seconds} seconds. Please wait and try again."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)
            self._history[(ip, endpoint)] = timestamps

    def reset(self):
        """Clear all logged timestamps across all clients (used for test isolation)."""
        with self._lock:
            self._history.clear()


limiter = SlidingWindowRateLimiter()


def rate_limit_auth(request: Request):
    """
    FastAPI dependency enforcing IP rate limiting on login and register.
    Configured via settings (AUTH_RATE_LIMIT_MAX_ATTEMPTS, AUTH_RATE_LIMIT_WINDOW_SECONDS).
    """
    settings = get_settings()
    if not settings.AUTH_RATE_LIMIT_ENABLED:
        return

    # Extract client IP; fallback to 127.0.0.1 for local/test clients
    client_ip = "127.0.0.1"
    if request.client and request.client.host:
        client_ip = request.client.host

    endpoint_key = request.url.path
    limiter.check(
        ip=client_ip,
        endpoint=endpoint_key,
        max_attempts=settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )


def reset_auth_limiter():
    """Reset the limiter for clean test runs."""
    limiter.reset()
