"""Tests for rate limiting and circuit breaker."""

from src.guardrails import RateLimiter, CircuitBreaker, CircuitState, Guardrails


class TestRateLimiter:
    """Test rate limiter."""

    def test_allow_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = RateLimiter(rate_per_minute=10)

        # Should allow up to 10 requests
        for _ in range(10):
            assert limiter.allow() is True

    def test_block_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(rate_per_minute=10)

        # Consume 10 tokens
        for _ in range(10):
            limiter.allow()

        # 11th request should be blocked
        assert limiter.allow() is False

    def test_get_remaining(self):
        """Test getting remaining tokens."""
        limiter = RateLimiter(rate_per_minute=10)
        assert limiter.get_remaining() == 10

        limiter.allow()
        assert limiter.get_remaining() == 9


class TestCircuitBreaker:
    """Test circuit breaker."""

    def test_circuit_starts_closed(self):
        """Test that circuit starts in closed state."""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED

    def test_record_success_keeps_circuit_closed(self):
        """Test that success keeps circuit closed."""
        breaker = CircuitBreaker()
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_record_multiple_successes(self):
        """Test multiple successes."""
        breaker = CircuitBreaker()
        for _ in range(3):
            breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_record_failures_opens_circuit(self):
        """Test that failures open the circuit when threshold reached."""
        breaker = CircuitBreaker(failure_threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

        # Third failure should open circuit
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_is_open_returns_true_when_open(self):
        """Test that is_open returns True when circuit is open."""
        breaker = CircuitBreaker(failure_threshold=1)
        breaker.record_failure()
        assert breaker.is_open() is True

    def test_is_open_returns_false_when_closed(self):
        """Test that is_open returns False when circuit is closed."""
        breaker = CircuitBreaker()
        assert breaker.is_open() is False

    def test_get_status(self):
        """Test getting circuit breaker status."""
        breaker = CircuitBreaker(failure_threshold=5)
        status = breaker.get_status()
        assert status["state"] == "closed"
        assert status["failures"] == 0
        assert status["threshold"] == 5

    def test_circuit_transitions_to_half_open(self):
        """Test that circuit transitions to half-open after recovery timeout."""
        import time
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout (0 seconds)
        time.sleep(0.01)
        assert breaker.is_open() is False
        assert breaker.state == CircuitState.HALF_OPEN


class TestGuardrails:
    """Test combined guardrails."""

    def test_check_read_rate_limit(self):
        """Test read rate limiting."""
        guardrails = Guardrails(read_rate_limit=10)

        # Should allow 10 reads
        for _ in range(10):
            assert guardrails.check_read() is True

        # 11th should be blocked
        assert guardrails.check_read() is False

    def test_guardrails_initialization(self):
        """Test that guardrails can be initialized."""
        guardrails = Guardrails(read_rate_limit=50)
        assert guardrails is not None
        assert guardrails.circuit_breaker is not None

    def test_check_write_rate_limit(self):
        """Test write rate limiting."""
        guardrails = Guardrails(write_rate_limit=5)

        # Should allow 5 writes
        for _ in range(5):
            assert guardrails.check_write() is True

        # 6th should be blocked
        assert guardrails.check_write() is False

    def test_check_dangerous_rate_limit(self):
        """Test dangerous operation rate limiting."""
        # dangerous_rate_limit=1 creates a limiter with 60 tokens/min (1*60)
        guardrails = Guardrails(dangerous_rate_limit=1)

        # Should allow multiple dangerous operations (60 per minute)
        for _ in range(10):
            assert guardrails.check_dangerous() is True

    def test_record_error(self):
        """Test recording errors for circuit breaker."""
        guardrails = Guardrails()
        guardrails.record_error()
        assert guardrails.circuit_breaker.state == CircuitState.CLOSED

    def test_record_success(self):
        """Test recording success."""
        guardrails = Guardrails()
        guardrails.record_success()
        assert guardrails.circuit_breaker.state == CircuitState.CLOSED

    def test_get_status(self):
        """Test getting guardrails status."""
        guardrails = Guardrails(read_rate_limit=50, write_rate_limit=5)
        status = guardrails.get_status()
        assert "read_remaining" in status
        assert "write_remaining" in status
        assert "dangerous_remaining" in status
        assert "circuit_breaker" in status

    def test_circuit_breaker_blocks_read(self):
        """Test that open circuit breaker blocks reads."""
        guardrails = Guardrails()
        guardrails.circuit_breaker.record_failure()
        guardrails.circuit_breaker.record_failure()
        guardrails.circuit_breaker.record_failure()
        guardrails.circuit_breaker.record_failure()
        guardrails.circuit_breaker.record_failure()
        assert guardrails.check_read() is False

    def test_circuit_breaker_blocks_write(self):
        """Test that open circuit breaker blocks writes."""
        guardrails = Guardrails()
        guardrails.circuit_breaker.record_failure()
        guardrails.circuit_breaker.record_failure()
        guardrails.circuit_breaker.record_failure()
        guardrails.circuit_breaker.record_failure()
        guardrails.circuit_breaker.record_failure()
        assert guardrails.check_write() is False
