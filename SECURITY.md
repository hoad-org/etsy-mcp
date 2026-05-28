# Security

Etsy MCP implements a NIST-aligned 5-layer defense-in-depth architecture.

## Architecture

### Layer 1: Input Boundary
- CLI validation of all inputs
- Rate limit checks (50 reads/min, 5 writes/min, 1 dangerous/5min)
- Circuit breaker pattern (5 errors → exponential backoff)

### Layer 2: Authorization
- Read-only operations (no confirmation required)
- Future: RBAC roles + confirmation gates for writes

### Layer 3: Credential Management
- AES-256-GCM encryption (NIST-approved)
- PBKDF2-SHA256 key derivation (600k iterations)
- Master key from `ETSY_VAULT_PASSWORD` environment variable
- Storage: `~/.etsy-mcp/credentials.enc` (0600 permissions)

### Layer 4: API Execution
- TLS 1.3 minimum (enforced via urllib3 context)
- Certificate pinning (Etsy root certificate)
- HMAC-SHA256 request signing
- 30-second timeout per request
- Response validation (HTTP status + JSON schema)

### Layer 5: Output Boundary
- Immutable JSONL audit logs
- HMAC-SHA256 integrity signatures (detect tampering)
- Strict redaction: API tokens, credentials NEVER logged
- 7-day raw retention, 2-year encrypted archive

## Threat Model

| Threat | Impact | Probability | Mitigation |
|--------|--------|-------------|-----------|
| Token theft | Critical | Medium | AES-256-GCM + PBKDF2 |
| Credential exposure in logs | Critical | Medium | Strict redaction + structured logging |
| Accidental bulk operations | High | High | Confirmation gates + dry-run (P2+) |
| Rate limit abuse/ban | High | Medium | Token bucket + circuit breaker |
| Code vulnerability/supply chain | Critical | Low | Code review + SCA |
| MITM on API | High | Very Low | TLS 1.3 + cert pinning |

## Compliance

- ✅ NIST CSF (Identify, Protect, Detect, Respond, Recover)
- ✅ NIST SP 800-53 (SC-7, SC-13, AU-2, AU-6)
- ✅ NIST FIPS (Cryptographic algorithms approved)
- ✅ OWASP API Security Top 10
- ✅ SOC 2 Type II ready (post-6 months ops + external audit)

## Procedures

### Token Rotation (Every 90 Days)

1. Generate new token in Etsy dashboard
2. Encrypt with `CryptoManager.encrypt(new_token, password)`
3. Update `~/.etsy-mcp/credentials.enc`
4. Verify with test read operation
5. Revoke old token immediately
6. Document in operations log

### Incident Response

**Token compromise:**
1. Revoke immediately in Etsy dashboard
2. Generate new token
3. Re-encrypt credentials
4. Audit logs automatically redact tokens
5. No manual cleanup required

**Log tampering:**
1. Stop operations
2. Verify HMAC signatures: `AuditLogger.verify_integrity(log_file)`
3. Investigate unauthorized entries
4. Restore from backup if needed

**Code vulnerability:**
1. Disable MCP immediately
2. Assess impact (audit logs)
3. Apply patch
4. Redeploy + test
5. Document in security log

## Best Practices

- Never log API tokens or credentials (automatic redaction)
- Rotate tokens every 90 days
- Use strong `ETSY_VAULT_PASSWORD` (>16 chars, mixed case/numbers/symbols)
- Keep audit logs for 7 days minimum
- Monitor circuit breaker for patterns (may indicate attack)
- Run `make security` before every commit

## Dependencies

Security-critical dependencies:
- `cryptography` — AES-256-GCM, PBKDF2
- `requests` — TLS 1.3 support
- `urllib3` — SSL context control

All dependencies scanned with:
```bash
bandit -r src/
```

## Testing

Security tests:
```bash
make security         # Run bandit
make check           # All checks (lint, type-check, security)
pytest tests/test_crypto.py     # Encryption tests
pytest tests/test_audit.py      # Audit log tests
pytest tests/test_guardrails.py # Rate limiting tests
```

## Reporting Security Issues

**Do not open public issues for security vulnerabilities.**

Email: security@hoad-org.dev

Include:
- Description of vulnerability
- Affected component
- Reproduction steps (if possible)
- Suggested fix (optional)
