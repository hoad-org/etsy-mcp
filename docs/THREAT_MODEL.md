# Threat Model & Risk Assessment

## Threat Landscape

### Threat 1: API Token Theft

**Description:** Attacker obtains unencrypted Etsy API token

**Attack Vectors:**
- Memory dump during execution
- Unencrypted storage on disk
- Environment variable exposure
- Log file disclosure
- GitHub commit history (if accidentally committed)

**Impact:**
- **Severity:** CRITICAL
- Full access to Etsy shop
- Ability to delete products, modify listings, process refunds
- Reputational damage

**Probability:** Medium
- Requires local access OR memory inspection
- OR requires repository breach

**Mitigation:**
- ✅ AES-256-GCM encryption at rest
- ✅ PBKDF2-SHA256 key derivation (600k iterations)
- ✅ Master key in `ETSY_VAULT_PASSWORD` env var (never stored)
- ✅ Redaction in logs (never logged, even encrypted)
- ✅ 0600 file permissions on credentials.enc
- ✅ Pre-commit hook blocks hardcoded secrets

**Residual Risk:** Low
- Master password compromise would expose key
- Mitigated by strong password requirement (CLAUDE.md documents this)

---

### Threat 2: Credential Exposure in Logs

**Description:** Sensitive data leaked through audit logs

**Attack Vectors:**
- Overly verbose logging of API requests
- Logging API tokens or request headers
- Unencrypted log storage
- Log file disclosure to attackers

**Impact:**
- **Severity:** CRITICAL
- Same as token theft
- Evidence trail for attackers

**Probability:** Medium
- Easy mistake during development
- Requires log file access

**Mitigation:**
- ✅ Automatic redaction of sensitive fields (api_token, password, etc.)
- ✅ HMAC-SHA256 signatures on logs (detect tampering)
- ✅ Review protocol: No secrets logged by code inspection
- ✅ Structured logging (easy to audit)
- ✅ Immutable JSONL format (can't be retroactively modified)

**Residual Risk:** Low
- Mitigation is automated, not manual
- Code review adds second layer

---

### Threat 3: Accidental Bulk Operations

**Description:** User accidentally deletes all products, clears inventory, etc.

**Attack Vectors:**
- Typo in product list filter (e.g., "delete all status=active")
- Misunderstanding of API parameters
- Script error (accidentally looping delete)

**Impact:**
- **Severity:** HIGH
- Loss of revenue (products unavailable for sale)
- Manual recovery needed

**Probability:** HIGH
- Humans make mistakes
- No guardrails in P1 (read-only)
- P2+ adds confirmation gates

**Mitigation (P1):**
- ✅ Read-only operations only (no delete/modify possible)

**Mitigation (P2+):**
- ✅ Confirmation gates: 1x for moderate writes, 2x for destructive
- ✅ Dry-run mode (preview changes before committing)
- ✅ 5-second cooldown before destructive ops
- ✅ Audit log shows what was attempted

**Residual Risk:** Very Low (P1), Low (P2+)

---

### Threat 4: Rate Limit Abuse / API Ban

**Description:** Too many API calls trigger Etsy rate limit, resulting in IP ban

**Attack Vectors:**
- Attacker repeatedly calls same operation
- Script bug causes infinite loop
- Compromised credentials (external attacker)

**Impact:**
- **Severity:** HIGH
- MCP becomes unusable
- Requires contacting Etsy support to unban

**Probability:** Medium
- Etsy rate limits are moderate
- Easy to exceed during testing

**Mitigation:**
- ✅ Token bucket rate limiter (50 reads/min)
- ✅ Circuit breaker: Opens after 5 errors in 60s
- ✅ Exponential backoff (prevents hammering)
- ✅ Audit log tracks all calls (can see if abused)

**Residual Risk:** Low
- Rate limiter is active from startup
- Circuit breaker prevents runaway requests

---

### Threat 5: Code Vulnerability / Supply Chain Attack

**Description:** Vulnerability in dependencies or MCP code itself

**Attack Vectors:**
- Malicious dependency (cryptography, requests, click)
- Code vulnerability (buffer overflow, injection)
- Backdoored dependency update

**Impact:**
- **Severity:** CRITICAL
- All mitigations bypassed
- Arbitrary code execution

**Probability:** Low
- Dependencies are well-maintained
- Code is reviewed before release

**Mitigation:**
- ✅ Minimal dependencies (only essential libraries)
- ✅ Pinned versions in pyproject.toml
- ✅ Bandit security scanner (pre-commit hook)
- ✅ Code review before release
- ✅ SCA (Software Composition Analysis) in CI/CD

**Residual Risk:** Very Low
- Mitigations are preventative (before release)
- Ongoing monitoring needed post-release

---

### Threat 6: MITM Attack on Etsy API

**Description:** Attacker intercepts API calls, steals token, modifies responses

**Attack Vectors:**
- Compromised network (corporate WiFi, public WiFi)
- DNS hijacking
- BGP hijacking

**Impact:**
- **Severity:** HIGH
- Token exposure
- Modified API responses could corrupt data

**Probability:** Very Low
- TLS 1.3 is extremely hard to break
- Certificate pinning prevents most attacks
- Requires sophisticated attacker

**Mitigation:**
- ✅ TLS 1.3 minimum (enforced via urllib3 context)
- ✅ Certificate pinning (Etsy root certificate)
- ✅ HMAC-SHA256 request signing
- ✅ Response validation (HTTP status + JSON schema)
- ✅ 30-second timeout (prevents slow network attacks)

**Residual Risk:** Very Low
- TLS 1.3 + pinning is state-of-the-art
- Attacker would need control of Etsy's infrastructure

---

## Risk Scoring Matrix

| Threat | Severity | Probability | Risk Score | Mitigation Status |
|--------|----------|-------------|------------|-------------------|
| Token theft | CRITICAL | Medium | 6/10 | Mitigated (encrypted) |
| Credential exposure in logs | CRITICAL | Medium | 6/10 | Mitigated (redacted) |
| Accidental bulk operations | HIGH | HIGH | 8/10 | Mitigated (read-only P1) |
| Rate limit abuse | HIGH | Medium | 5/10 | Mitigated (rate limiter) |
| Code vulnerability | CRITICAL | Low | 2/10 | Mitigated (SCA, code review) |
| MITM attack | HIGH | Very Low | 1/10 | Mitigated (TLS 1.3 + pinning) |

**Overall Risk Level:** LOW-MEDIUM
- All critical threats have mitigations
- Residual risks are manageable
- Security posture improves from P1 → P4

---

## Incident Response Procedures

### Token Compromise

**Detection:**
- User reports unauthorized activity
- Audit log shows requests from unexpected IP
- Etsy support reports suspicious activity

**Response:**
1. **Immediately:** Revoke token in Etsy dashboard
2. **5 min:** Generate new token
3. **10 min:** Re-encrypt new token, update credentials.enc
4. **15 min:** Verify with test read operation
5. **20 min:** Run audit log analysis:
   - Who called what
   - What data was accessed
   - What changes were made
6. **1 hour:** Contact affected customers if needed

**Prevention:**
- Rotate tokens every 90 days
- Monitor audit logs for anomalies
- Alert on requests from new IPs

---

### Log Tampering

**Detection:**
- HMAC signature verification fails: `AuditLogger.verify_integrity(log_file)`
- Missing audit entries for known operations

**Response:**
1. **Immediately:** Stop MCP operations
2. **5 min:** Verify HMAC signatures on all logs
3. **10 min:** Restore from backup (7-day archive)
4. **15 min:** Determine what was modified
5. **1 hour:** Investigate cause (malware, unauthorized access)
6. **2 hours:** Patch vulnerability if code-related

**Prevention:**
- Daily signature verification (automated)
- Backup logs to S3 (encrypted, separate account)
- Alert on signature failures

---

### Code Vulnerability

**Detection:**
- Security researcher reports issue
- Internal code review finds vulnerability
- Bandit security scanner flags it

**Response:**
1. **Immediately:** Disable MCP (if severe)
2. **30 min:** Assess impact:
   - What's exploitable
   - Has it been exploited
   - How many users affected
3. **1 hour:** Develop patch
4. **2 hours:** Code review patch
5. **3 hours:** Deploy patch
6. **4 hours:** Verify fix with tests

**Prevention:**
- Pre-commit Bandit scanning
- Code review before release
- Dependency scanning (SCA)
- Incident response drills (quarterly)

---

## Security Assumptions

### Assumptions We Make (Must Be True)

1. **Master password is strong**
   - Requirement: >16 chars, mixed case/numbers/symbols
   - Assumption: User follows this
   - Mitigated by: Documentation, error messages

2. **ETSY_VAULT_PASSWORD is not logged**
   - Assumption: User doesn't accidentally log it
   - Mitigated by: Env var usage (not passed as arguments)

3. **~/.etsy-mcp/credentials.enc file permissions are correct**
   - Assumption: File is 0600 (only owner can read)
   - Mitigated by: Automatic during first run

4. **Etsy API key is valid**
   - Assumption: User provides real, authorized key
   - Mitigated by: Test call on startup

### Assumptions We DON'T Make (Safe to Assume False)

1. ❌ Attacker has access to ~/.etsy-mcp/ directory
   - Mitigated by: AES-256-GCM encryption

2. ❌ Attacker can see memory during execution
   - Mitigated by: No plaintext storage, cleared after use

3. ❌ Attacker has network access to Etsy API
   - Mitigated by: TLS 1.3 + certificate pinning

4. ❌ Attacker can modify source code before execution
   - Mitigated by: Code review, SCA, integrity checks

---

## Security Testing Checklist

**Before every release:**
- [ ] All unit tests pass (>85% coverage)
- [ ] `bandit -r src/` finds no issues
- [ ] `mypy --strict` passes
- [ ] No hardcoded secrets in code
- [ ] All sensitive fields logged with redaction
- [ ] HMAC signatures on all logs
- [ ] TLS 1.3 enforced (openssl s_client verification)
- [ ] Rate limiter + circuit breaker tested
- [ ] Encryption roundtrip tested with real password

**Quarterly:**
- [ ] Incident response drill (simulate token theft)
- [ ] Security code review (third-party)
- [ ] Penetration testing (internal)
- [ ] Threat model review (updated risks)

---

**Threat Model Version:** 2.0
**Status:** Complete for P1
**Last Updated:** 2026-05-28
**Next Review:** 2026-08-28
