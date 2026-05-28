"""Rate limiter and circuit breaker for API safety."""

import time
from collections import deque
from enum import Enum
from typing import Any


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate_per_minute: int) -> None:
        """
        Initialize rate limiter.

        Args:
            rate_per_minute: Tokens per minute
        """
        self.rate_per_minute = rate_per_minute
        self.tokens = float(rate_per_minute)
        self.last_refill = time.time()

    def allow(self) -> bool:
        """Check if request is allowed."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.rate_per_minute, self.tokens + elapsed * (self.rate_per_minute / 60))
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True

        return False

    def get_remaining(self) -> int:
        """Get remaining tokens."""
        return int(self.tokens)


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        window_size: int = 60,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting half-open
            window_size: Seconds for failure window
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window_size = window_size

        self.state = CircuitState.CLOSED
        self.failures: deque[float] = deque()
        self.last_failure = 0.0
        self.opened_at = 0.0

    def record_failure(self) -> None:
        """Record a failure."""
        now = time.time()
        self.last_failure = now
        self.failures.append(now)

        # Clean old failures outside window
        while self.failures and self.failures[0] < now - self.window_size:
            self.failures.popleft()

        # Open circuit if threshold reached
        if len(self.failures) >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = now

    def record_success(self) -> None:
        """Record a success."""
        self.failures.clear()
        self.state = CircuitState.CLOSED

    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == CircuitState.OPEN:
            now = time.time()
            if now - self.opened_at >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return False
            return True
        return False

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "state": self.state.value,
            "failures": len(self.failures),
            "threshold": self.failure_threshold,
        }


class Guardrails:
    """Combined rate limiter and circuit breaker."""

    def __init__(
        self,
        read_rate_limit: int = 50,
        write_rate_limit: int = 5,
        dangerous_rate_limit: int = 1,
    ) -> None:
        """Initialize guardrails."""
        self.read_limiter = RateLimiter(read_rate_limit)
        self.write_limiter = RateLimiter(write_rate_limit)
        self.dangerous_limiter = RateLimiter(dangerous_rate_limit * 60)  # 1 per 5 min
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    def check_read(self) -> bool:
        """Check if read operation is allowed."""
        if self.circuit_breaker.is_open():
            return False
        return self.read_limiter.allow()

    def check_write(self) -> bool:
        """Check if write operation is allowed."""
        if self.circuit_breaker.is_open():
            return False
        return self.write_limiter.allow()

    def check_dangerous(self) -> bool:
        """Check if dangerous operation is allowed."""
        if self.circuit_breaker.is_open():
            return False
        return self.dangerous_limiter.allow()

    def record_error(self) -> None:
        """Record API error for circuit breaker."""
        self.circuit_breaker.record_failure()

    def record_success(self) -> None:
        """Record successful API call."""
        self.circuit_breaker.record_success()

    def get_status(self) -> dict[str, Any]:
        """Get guardrails status."""
        return {
            "read_remaining": self.read_limiter.get_remaining(),
            "write_remaining": self.write_limiter.get_remaining(),
            "dangerous_remaining": self.dangerous_limiter.get_remaining(),
            "circuit_breaker": self.circuit_breaker.get_status(),
        }
