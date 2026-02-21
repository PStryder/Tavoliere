import time
from collections import defaultdict, deque


class RateLimitError(Exception):
    def __init__(self, limit_type: str, message: str):
        self.limit_type = limit_type
        self.message = message
        super().__init__(message)


class RateLimiter:
    """Per-seat sliding window rate limiter."""

    def __init__(self):
        # (seat_id, limit_type) -> deque of timestamps
        self._windows: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, seat_id: str, limit_type: str, max_count: int, window_s: float) -> None:
        """Raise RateLimitError if the rate limit is exceeded."""
        key = (seat_id, limit_type)
        now = time.monotonic()
        window = self._windows[key]

        # Purge expired entries
        cutoff = now - window_s
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= max_count:
            raise RateLimitError(
                limit_type=limit_type,
                message=f"Rate limit exceeded: {limit_type} (max {max_count} per {window_s}s)",
            )

        window.append(now)

    def clear(self) -> None:
        self._windows.clear()
