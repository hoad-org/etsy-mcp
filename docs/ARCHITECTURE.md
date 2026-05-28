# Etsy MCP - Complete Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude (User Interface)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ MCP Protocol
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Etsy MCP Server (P1)                        │
├─────────────────────────────────────────────────────────────────┤
│  5-Layer Defense-in-Depth Architecture                          │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5: Output Boundary                                        │
│   └─ Immutable JSONL Audit Logs + HMAC-SHA256 Signatures      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: API Execution                                          │
│   ├─ TLS 1.3 Minimum                                           │
│   ├─ Certificate Pinning                                        │
│   ├─ HMAC-SHA256 Request Signing                               │
│   ├─ Response Validation (HTTP Status + JSON Schema)           │
│   └─ 30-Second Timeout per Request                             │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Credential Management                                  │
│   ├─ AES-256-GCM Encryption                                    │
│   ├─ PBKDF2-SHA256 Key Derivation (600k iterations)           │
│   └─ Storage: ~/.etsy-mcp/credentials.enc (0600 perms)        │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Authorization                                          │
│   ├─ Read-Only (no confirmation gates)                         │
│   ├─ Write (confirmation gates in P2+)                         │
│   └─ Dangerous Ops (2x confirmation + cooldown in P2+)         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: Input Boundary                                         │
│   ├─ CLI Validation                                             │
│   ├─ Token Bucket Rate Limiting                                │
│   │   ├─ Read: 50/min                                          │
│   │   ├─ Write: 5/min (P2+)                                    │
│   │   └─ Dangerous: 1/5min (P2+)                               │
│   └─ Circuit Breaker Pattern                                    │
│       └─ Opens after 5 errors in 60s, exponential backoff      │
├─────────────────────────────────────────────────────────────────┤
│  Tools (Claude-Callable)                                        │
│   ├─ get_shop_info()         → Shop details                    │
│   ├─ list_products()         → Products with pagination        │
│   ├─ get_product()           → Single product                  │
│   └─ list_orders()           → Recent orders                   │
└─────────────────────────────────────────────────────────────────┘
                             │ HTTPS (TLS 1.3)
                             ▼
                    ┌─────────────────┐
                    │   Etsy API      │
                    │ (openapi.etsy.com)
                    └─────────────────┘
```

## Data Flow

### Read Operation (get_shop_info)

```
Claude calls: get_shop_info()
    ↓
MCP Server receives request
    ↓
Check rate limit (Layer 1)
    ├─ Token bucket: 50 reads/min
    ├─ Circuit breaker: Is open?
    └─ Allow/Block decision
    ↓
Load encrypted credentials (Layer 3)
    ├─ Decrypt API key (AES-256-GCM)
    └─ Master key from ETSY_VAULT_PASSWORD
    ↓
Call Etsy API (Layer 4)
    ├─ TLS 1.3 connection
    ├─ Sign request (HMAC-SHA256)
    ├─ Validate response (JSON schema)
    └─ 30-second timeout
    ↓
Log action to audit (Layer 5)
    ├─ JSONL format
    ├─ Redact sensitive fields (no tokens logged)
    ├─ HMAC-SHA256 signature
    └─ Store in ~/.etsy-mcp/audit/YYYY-MM-DD.jsonl
    ↓
Return result to Claude
```

## Configuration Hierarchy (4-Level)

```
Priority (highest → lowest):
    1. Environment Variables
       └─ ETSY_API_KEY, ETSY_VAULT_PASSWORD, etc.
    ↑
    2. Repo Config (./.etsy-mcp/config.json)
       └─ Project-specific settings
    ↑
    3. Master Config (~/.etsy-mcp/config.json)
       └─ User-level defaults
    ↑
    4. Code Defaults (src/config.py)
       └─ Hardcoded minimums
```

## Security Controls Matrix

| Control | Layer | Implementation | Verification |
|---------|-------|-----------------|--------------|
| Input validation | Layer 1 | CLI schema validation | test_config.py |
| Rate limiting | Layer 1 | Token bucket (50/min) | test_guardrails.py |
| Circuit breaker | Layer 1 | 5 errors → opens | test_guardrails.py |
| Encryption at rest | Layer 3 | AES-256-GCM | test_crypto.py |
| Key derivation | Layer 3 | PBKDF2-SHA256 (600k) | test_crypto.py |
| TLS 1.3 | Layer 4 | urllib3 context enforcement | Integration tests |
| Request signing | Layer 4 | HMAC-SHA256 per request | etsy_api.py |
| Response validation | Layer 4 | HTTP status + JSON schema | etsy_api.py |
| Audit logging | Layer 5 | Immutable JSONL | test_audit.py |
| Log integrity | Layer 5 | HMAC-SHA256 signatures | test_audit.py |
| Field redaction | Layer 5 | Automatic (api_token, password, etc.) | test_audit.py |

## File Structure

```
etsy-mcp/
├── src/
│   ├── __init__.py
│   ├── crypto.py          # Layer 3: AES-256-GCM + PBKDF2
│   ├── config.py          # Config hierarchy (4-level)
│   ├── audit.py           # Layer 5: JSONL + HMAC logging
│   ├── etsy_api.py        # Layer 4: TLS 1.3 + signing
│   ├── guardrails.py      # Layer 1: Rate limiter + circuit breaker
│   ├── server.py          # MCP server + tool routing
│   └── tools/             # (Future: individual tool modules)
├── tests/
│   ├── test_crypto.py     # Encryption roundtrip, key derivation
│   ├── test_config.py     # 4-level hierarchy, type conversions
│   ├── test_audit.py      # Log creation, integrity, redaction
│   ├── test_guardrails.py # Rate limiting, circuit breaker
│   ├── test_server.py     # MCP protocol, tool routing
│   └── integration/       # End-to-end flows
├── docs/
│   ├── ARCHITECTURE.md    # This file
│   ├── DESIGN.md          # Complete design spec
│   ├── THREAT_MODEL.md    # Threat analysis
│   └── OPERATIONAL_PROCEDURES.md
├── .claude/
│   └── CLAUDE.md          # Development guide
├── SECURITY.md            # Security procedures
├── README.md              # User guide
├── .env.example           # Template (no values)
├── pyproject.toml         # Dependencies
├── Makefile               # Build targets
└── .gitignore             # Exclude secrets
```

## Compliance & Standards

**NIST Framework:**
- ✅ NIST CSF: Identify, Protect, Detect, Respond, Recover
- ✅ NIST SP 800-53: SC-7 (boundary protection), SC-13 (cryptography), AU-2 (audit events), AU-6 (audit review)
- ✅ NIST FIPS: All cryptographic algorithms approved

**Industry Standards:**
- ✅ OWASP API Security Top 10
- ✅ OWASP Top 10 Web Application Security
- ✅ CWE Top 25 (covered)

**Audit-Ready:**
- ✅ SOC 2 Type II ready (post-6 months ops + external audit)
- ✅ Immutable audit trail
- ✅ Incident response documented

## Deployment Model

**P1 (Current): Local + Encrypted Storage**
- MCP server runs locally (single machine)
- Credentials encrypted on disk
- Audit logs in ~/.etsy-mcp/audit/

**Future (P4): Serverless AWS**
- AWS Lambda for MCP server
- AWS Secrets Manager for credentials
- DynamoDB for audit logs + products
- Step Functions for automation workflows

---

**Architecture Version:** 2 (Reliability-Optimized)
**Status:** Production Ready for P1 (Read-Only)
**Last Updated:** 2026-05-28
