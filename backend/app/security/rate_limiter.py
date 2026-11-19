"""
In-memory sliding-window rate limiter for protecting authentication endpoints against brute force attacks.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from backend.app.config.settings import get_settings
from backend.app.core.exceptions import AppException

settings = get_settings()


class RateLimitExceededError(AppException):
    """Raised when an operation exceeds allowed rate limits."""
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            message=f"Too many failed login attempts. Please try again in {retry_after} seconds.",
            status_code=429,
            details={"retry_after": retry_after}
        )


class LoginRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter for login attempts.
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._attempts: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """
        Checks whether an attempt for the given key is allowed under the rate limit.
        Returns (is_allowed, retry_after_seconds).
        """
        now = time.monotonic()
        window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
        max_attempts = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS

        with self._lock:
            queue = self._attempts[key]
            # Prune attempts older than the rate limit window
            while queue and queue[0] < now - window:
                queue.popleft()

            if len(queue) >= max_attempts:
                oldest = queue[0]
                retry_after = max(1, int(oldest + window - now))
                return False, retry_after

            return True, 0

    def record_failure(self, key: str) -> None:
        """Records a failed attempt for the specified key."""
        now = time.monotonic()
        with self._lock:
            self._attempts[key].append(now)

    def record_success(self, key: str) -> None:
        """Clears recorded failures upon a successful login."""
        with self._lock:
            if key in self._attempts:
                del self._attempts[key]

    def clear(self) -> None:
        """Clears all tracking data (primarily for test resets)."""
        with self._lock:
            self._attempts.clear()


# Global singleton instance
login_rate_limiter = LoginRateLimiter()
