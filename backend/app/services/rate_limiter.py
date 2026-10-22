"""
In-memory sliding window rate limiter for security-sensitive auth endpoints.
Thread-safe, zero external dependencies, configurable via .env.

Supports:
- Distinguishing failed attempts (on /auth/login, only failures count against the budget)
- Safe proxy support (reads X-Forwarded-For only when AUTH_TRUST_PROXY=true)
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

    def is_blocked(
        self, ip: str, endpoint: str, max_attempts: int, window_seconds: int
    ) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = [t for t in self._history[(ip, endpoint)] if t > cutoff]
            self._history[(ip, endpoint)] = timestamps

            if len(timestamps) >= max_attempts:
                oldest_in_window = timestamps[0]
                retry_after = max(1, int(math.ceil(window_seconds - (now - oldest_in_window))))
                return True, retry_after

            return False, 0

    def record_attempt(self, ip: str, endpoint: str):
        """Record an attempt timestamp for an IP and endpoint."""
        now = time.time()
        with self._lock:
            self._history[(ip, endpoint)].append(now)

    def check_and_record(
        self, ip: str, endpoint: str, max_attempts: int, window_seconds: int
    ):
        """Check if blocked; if not, record the attempt. Used for /auth/register."""
        blocked, retry_after = self.is_blocked(ip, endpoint, max_attempts, window_seconds)
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Too many attempts. Maximum allowed is {max_attempts} attempt(s) per "
                    f"{window_seconds} seconds. Please wait and try again."
                ),
                headers={"Retry-After": str(retry_after)},
            )
        self.record_attempt(ip, endpoint)

    def reset(self):
        """Clear all logged timestamps across all clients (used for test isolation)."""
        with self._lock:
            self._history.clear()


limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Resolve client IP address safely.
    Only inspects 'X-Forwarded-For' if AUTH_TRUST_PROXY=true in configuration.
    """
    settings = get_settings()
    if settings.AUTH_TRUST_PROXY:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # First IP in the comma-separated chain is the client
            return forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def check_login_rate_limit(request: Request):
    """
    FastAPI dependency for /auth/login: checks if the client IP is currently blocked
    due to exceeding the allowed failed attempts within the sliding window.
    Does NOT record an attempt; failures are recorded explicitly when auth fails.
    """
    settings = get_settings()
    if not settings.AUTH_RATE_LIMIT_ENABLED:
        return

    client_ip = get_client_ip(request)
    endpoint_key = request.url.path

    blocked, retry_after = limiter.is_blocked(
        ip=client_ip,
        endpoint=endpoint_key,
        max_attempts=settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Too many failed login attempts. Maximum allowed is {settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS} "
                f"attempt(s) per {settings.AUTH_RATE_LIMIT_WINDOW_SECONDS} seconds. Please wait and try again."
            ),
            headers={"Retry-After": str(retry_after)},
        )


def record_login_failure(request: Request):
    """Record a failed login attempt for the client's IP."""
    settings = get_settings()
    if not settings.AUTH_RATE_LIMIT_ENABLED:
        return
    client_ip = get_client_ip(request)
    endpoint_key = request.url.path
    limiter.record_attempt(ip=client_ip, endpoint=endpoint_key)


def rate_limit_register(request: Request):
    """
    FastAPI dependency for /auth/register: limits rapid user account creations.
    """
    settings = get_settings()
    if not settings.AUTH_RATE_LIMIT_ENABLED:
        return

    client_ip = get_client_ip(request)
    endpoint_key = request.url.path
    limiter.check_and_record(
        ip=client_ip,
        endpoint=endpoint_key,
        max_attempts=settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )


# For backward compatibility with imports
rate_limit_auth = check_login_rate_limit


def reset_auth_limiter():
    """Reset the limiter for clean test runs."""
    limiter.reset()
