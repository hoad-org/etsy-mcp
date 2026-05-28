# Etsy MCP Development Guide

## Overview

This is a security-first MCP implementation for Etsy store management. Every line of code must pass security review.

## Architecture: 5-Layer Defense

```
Layer 5: Output Boundary (Audit Logs + HMAC)
    ↓
Layer 4: API Execution (TLS 1.3, Signing, Validation)
    ↓
Layer 3: Credential Management (AES-256-GCM, PBKDF2)
    ↓
Layer 2: Authorization (Confirmation Gates)
    ↓
Layer 1: Input Boundary (Rate Limiting, Circuit Breaker)
```

Each layer is tested independently.

## Key Files

- `src/crypto.py` — AES-256-GCM encryption + PBKDF2 key derivation
- `src/config.py` — 4-level configuration hierarchy
- `src/audit.py` — JSONL logging + HMAC integrity
- `src/etsy_api.py` — Etsy API client (TLS 1.3, request signing)
- `src/guardrails.py` — Rate limiter + circuit breaker
- `src/server.py` — MCP server entry point

## Development Workflow

### Before Coding
1. Read `SECURITY.md` (threat model, compliance)
2. Understand the 5-layer architecture
3. Check which layer your change touches

### While Coding
1. **Never commit secrets** (use env vars, not hardcoded values)
2. **Test each layer independently** (don't mix concerns)
3. **Redact sensitive data in logs** (automatic via audit.py)
4. **Run type-checking** (mypy --strict is non-negotiable)

### Before Commit
```bash
make check          # All checks must pass
make coverage       # Must be >85%
bandit -r src/      # No security issues
```

## Testing Strategy

**Target: >85% coverage**

- `test_crypto.py` — Encryption roundtrip, key derivation, password failures
- `test_config.py` — 4-level hierarchy, type conversions, env overrides
- `test_audit.py` — Log creation, redaction, HMAC verification
- `test_guardrails.py` — Rate limiting, circuit breaker, error handling
- `test_server.py` — MCP protocol, tool routing, error handling

## Common Tasks

### Add a new read-only tool
1. Add tool schema to `server.py` (list_tools)
2. Implement tool logic in `call_tool()`
3. Add audit logging (automatic redaction)
4. Add unit test
5. Run `make check` and `make coverage`

### Encrypt API credentials
```python
from src.crypto import CryptoManager

# Encrypt
encrypted = CryptoManager.encrypt(api_key, password)

# Decrypt (in production)
decrypted = CryptoManager.decrypt(encrypted, password)
```

### Log an action
```python
from src.audit import AuditLogger

logger = AuditLogger("~/.etsy-mcp/audit/")
logger.log("action_name", {"details": "data"}, redact=["api_token"])
```

### Check rate limits
```python
from src.guardrails import Guardrails

guardrails = Guardrails(read_rate_limit=50)
if guardrails.check_read():
    # Allowed
else:
    # Blocked
```

## Security Checklist

Before every commit:
- [ ] No hardcoded API keys, tokens, or passwords
- [ ] All sensitive fields logged with redaction
- [ ] HMAC signatures on audit logs
- [ ] TLS 1.3 enforced on API calls
- [ ] Rate limiter + circuit breaker active
- [ ] Unit tests for encryption, audit, guardrails
- [ ] `make check` passes (lint, type, security)
- [ ] Coverage >85%

## Deployment

P1 is read-only and low-risk:
1. Pass all tests and security checks
2. Get code review from security-conscious peer
3. Deploy to staging
4. Verify audit logs are immutable
5. Deploy to production

## Roadmap

- **P1** — Read-only operations (current)
- **P2** — Confirmation gates for writes
- **P3** — Async bulk operations
- **P4** — AWS Step Functions integration

---

**Remember:** This is production code managing real Etsy stores. Every line matters.
