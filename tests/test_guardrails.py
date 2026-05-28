"""Tests for guardrails module (rate limiting and circuit breaker)."""

import time
import pytest
from src.guardrails import RateLimiter, CircuitBreaker, Guardrails, CircuitState


class TestRateLimiter:
    """Test token bucket rate limiter."""

    def test_allow_within_limit(self) -> None:
        """Test that requests within limit are allowed."""
        limiter = RateLimiter(60)  # 60 per minute

        # First request should pass
        assert limiter.allow()

    def test_block_over_limit(self) -> None:
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(1)  # 1 per minute

        # First request passes
        assert limiter.allow()

        # Second request blocked
        assert not limiter.allow()

    def test_token_refill(self) -> None:
        """Test that tokens refill over time."""
        limiter = RateLimiter(60)  # 60 per minute

        # Exhaust tokens
        limiter.tokens = 0

        # Wait 1 second (should refill 1 token)
        time.sleep(1)

        # Should now have ~1 token
        assert limiter.allow()


class TestCircuitBreaker:
    """Test circuit breaker for fault tolerance."""

    def test_circuit_closes_on_success(self) -> None:
        """Test circuit closes after success."""
        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_opens_on_threshold(self) -> None:
        """Test circuit opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open()

    def test_circuit_half_open_after_timeout(self) -> None:
        """Test circuit enters half-open after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        for _ in range(2):
            breaker.record_failure()

        assert breaker.is_open()

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should now be half-open
        assert not breaker.is_open()
        assert breaker.state == CircuitState.HALF_OPEN


class TestGuardrails:
    """Test combined guardrails."""

    def test_check_read_rate_limit(self) -> None:
        """Test read rate limiting."""
        guardrails = Guardrails(read_rate_limit=1)

        assert guardrails.check_read()
        assert not guardrails.check_read()

    def test_check_circuit_breaker(self) -> None:
        """Test circuit breaker blocks requests."""
        guardrails = Guardrails(read_rate_limit=100)

        # Trigger circuit breaker
        for _ in range(5):
            guardrails.record_error()

        # Should be blocked
        assert not guardrails.check_read()

    def test_status_reporting(self) -> None:
        """Test status reporting."""
        guardrails = Guardrails()
        status = guardrails.get_status()

        assert "read_remaining" in status
        assert "circuit_breaker" in status
        assert status["circuit_breaker"]["state"] == "closed"
