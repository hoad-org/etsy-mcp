# Etsy MCP - Complete Design Specification

## Product Vision

A production-grade Model Context Protocol (MCP) for secure Etsy store management. Claude can directly manage all aspects of an Etsy shop without exposing credentials or creating security vulnerabilities.

**Guiding Principle:** Actually secure, not "secure enough." Every control maps to NIST standards, threat actors are modeled, and incident procedures are documented.

## Phase-Based Rollout

### Phase 1: Read-Only MCP (3 weeks) ✅
**What:** Secure read operations with full security stack
**Tools:**
- `get_shop_info()` — Shop name, rating, product count
- `list_products()` — Paginated product list
- `get_product()` — Single product details
- `list_orders()` — Recent orders

**Security:** All 5 layers active
- Encryption: AES-256-GCM (credentials at rest)
- API: TLS 1.3, request signing
- Audit: Immutable JSONL logs
- Guardrails: Rate limiter + circuit breaker
- Authorization: No confirmation required (read-only)

**Success Criteria:**
- All unit tests pass (>85% coverage)
- All code quality tools pass (ruff, black, mypy, bandit)
- Audit logs are cryptographically signed
- TLS 1.3 enforced on API calls
- Rate limiter prevents ban
- Circuit breaker activates on errors

### Phase 2: Design System + Canva (2-3 weeks)
**What:** Auto-generate product designs, review, approve
**Components:**
- Template library (category → Canva template)
- Claude design generation
- Human review gate
- Design asset storage

**New Controls:**
- Confirmation gates (1x approval)
- Dry-run mode (preview before commit)

### Phase 3: Product Storage (1-2 weeks)
**What:** Store designed products in DynamoDB
**Components:**
- Product metadata table
- Status tracking (awaiting_review → published)
- Query by status
- Design versioning

**Infrastructure:**
- AWS DynamoDB (serverless, scalable)
- CloudWatch monitoring
- Automated backups

### Phase 4: Live Publishing (2 weeks)
**What:** Publish product from P3 → Live Etsy shop
**Components:**
- `create_product()` — New listing
- `upload_listing_image()` — Design as product photo
- `publish_product()` — Go live

**New Controls:**
- 2x confirmation gates (destructive)
- 5-second cooldown before publish
- Rollback procedures documented

## Technical Specification

### Encryption Scheme

**Algorithm:** AES-256-GCM (NIST-approved)
- Key size: 256 bits
- Nonce: 96 bits (random per encryption)
- Auth tag: 128 bits (automatically appended)

**Key Derivation:** PBKDF2-SHA256
- Iterations: 600,000 (NIST recommendation)
- Salt: 128 bits (random per credential)
- Output: 256-bit key

**Storage Format:** Base64(salt + nonce + ciphertext + auth_tag)

**Example:**
```python
from src.crypto import CryptoManager

# Encrypt credential
password = os.environ["ETSY_VAULT_PASSWORD"]
api_key = "your-etsy-api-key"
encrypted = CryptoManager.encrypt(api_key, password)

# Decrypt in production
decrypted = CryptoManager.decrypt(encrypted, password)
```

### Rate Limiting

**Token Bucket Algorithm**

```
P1 (Read-Only):
  - Read operations: 50 tokens/minute
  - Circuit breaker: 5 errors → opens (exponential backoff)
  - Recovery timeout: 60 seconds

P2+ (Write Operations):
  - Write operations: 5 tokens/minute
  - Dangerous operations: 1 token/5 minutes
  - Confirmation gates: 1x-2x depending on risk
```

**Circuit Breaker States:**
- **CLOSED** — Normal operation, requests allowed
- **OPEN** — Error threshold exceeded, requests blocked
- **HALF_OPEN** — Recovery timeout passed, testing single request
- → Back to CLOSED if request succeeds

### Audit Logging

**Format:** JSONL (one entry per line)

```json
{
  "timestamp": "2026-05-28T14:23:45.123456",
  "action": "get_shop_info",
  "details": {
    "status": "success",
    "shop_id": "12345",
    "execution_time_ms": 245
  },
  "_signature": "f8e3d2a1b9c4e5f6..."
}
```

**Redaction Rules:**
- `api_token` → `[REDACTED]`
- `api_key` → `[REDACTED]`
- `password` → `[REDACTED]`
- `vault_password` → `[REDACTED]`
- `secret` → `[REDACTED]`
- `credentials` → `[REDACTED]`

**Integrity Checking:**
```python
from src.audit import AuditLogger

logger = AuditLogger("~/.etsy-mcp/audit/")

# Verify log file integrity
is_valid = logger.verify_integrity(log_file_path)
if not is_valid:
    # Log tampering detected
    alert_security_team()
```

**Retention:**
- Raw logs: 7 days (local storage)
- Encrypted archive: 2 years (cloud backup)
- Daily rotation (YYYY-MM-DD.jsonl)

### Configuration Hierarchy

```python
# Priority order (highest wins)

# 1. Environment Variables (highest priority)
config.etsy_api_key = os.environ.get("ETSY_API_KEY")

# 2. Repo Config (./.etsy-mcp/config.json)
with open(".etsy-mcp/config.json") as f:
    repo_config = json.load(f)
    config.update(repo_config)

# 3. Master Config (~/.etsy-mcp/config.json)
with open(Path.home() / ".etsy-mcp" / "config.json") as f:
    master_config = json.load(f)
    config.update(master_config)

# 4. Code Defaults (lowest priority)
config.read_rate_limit = 50  # reads/minute
config.tls_verify = True
```

## API Contracts

### Tool: get_shop_info()

**Input:** None

**Output:**
```json
{
  "shop_id": 123456,
  "shop_name": "My Etsy Shop",
  "shop_url": "https://www.etsy.com/shop/myshop",
  "description": "Handmade crafts...",
  "rating": 4.8,
  "review_count": 342,
  "product_count": 45,
  "follower_count": 1200,
  "active_listings": 42,
  "total_sales": 5234
}
```

### Tool: list_products()

**Input:**
```python
{
  "status": "active",    # active, draft, sold_out
  "limit": 20,           # 1-100
  "offset": 0            # pagination
}
```

**Output:**
```json
{
  "listings": [
    {
      "listing_id": 456789,
      "title": "Handmade Ceramic Mug",
      "description": "...",
      "price": 24.99,
      "currency": "USD",
      "quantity": 5,
      "views": 234,
      "favorites": 12,
      "created_date": "2026-01-15",
      "updated_date": "2026-05-28",
      "tags": ["ceramic", "mug", "handmade"],
      "category": "pottery"
    }
  ],
  "count": 42,
  "pagination": {
    "offset": 0,
    "limit": 20
  }
}
```

### Tool: get_product()

**Input:**
```python
{
  "listing_id": 456789
}
```

**Output:**
```json
{
  "listing_id": 456789,
  "title": "Handmade Ceramic Mug",
  "description": "...",
  "price": 24.99,
  "quantity": 5,
  "images": [
    {
      "url": "https://...",
      "position": 0
    }
  ],
  "sections": ["kitchen", "home-decor"],
  "tags": ["ceramic", "mug"],
  "materials": ["ceramic", "glaze"],
  "shipping_template": "standard"
}
```

### Tool: list_orders()

**Input:**
```python
{
  "limit": 20,
  "offset": 0
}
```

**Output:**
```json
{
  "orders": [
    {
      "order_id": "9876543",
      "buyer": "customer_username",
      "total": 49.98,
      "currency": "USD",
      "created_date": "2026-05-25",
      "status": "shipped",
      "items_count": 2,
      "shipping_address": {
        "city": "Portland",
        "state": "OR",
        "country": "US"
      }
    }
  ],
  "count": 342,
  "pagination": {
    "offset": 0,
    "limit": 20
  }
}
```

## Error Handling

**Rate Limit Exceeded:**
```json
{
  "error": "Rate limit exceeded",
  "remaining_tokens": 0,
  "reset_at": "2026-05-28T14:24:45Z",
  "retry_after_seconds": 30
}
```

**Circuit Breaker Open:**
```json
{
  "error": "Circuit breaker is open",
  "reason": "Too many errors (5 in last 60s)",
  "recovery_time_seconds": 45
}
```

**API Error:**
```json
{
  "error": "Etsy API error",
  "status_code": 403,
  "details": "Invalid API key"
}
```

## Testing Strategy

**Target: >85% Coverage**

| Module | Tests | Coverage |
|--------|-------|----------|
| crypto.py | Encryption roundtrip, key derivation, password failures | >95% |
| config.py | 4-level hierarchy, env overrides, type conversions | >90% |
| audit.py | Log creation, redaction, HMAC verification | >90% |
| guardrails.py | Rate limiting, circuit breaker state transitions | >95% |
| etsy_api.py | Mocked API calls, TLS enforcement, request signing | >85% |
| server.py | MCP protocol, tool routing, error handling | >85% |

**Integration Tests:**
- Full read flow (auth → rate limit → API call → logging)
- Error handling (circuit breaker triggers, timeout handling)
- Configuration hierarchy (env var overrides, file loading)

---

**Design Version:** 2.0
**Status:** Complete for P1 (Read-Only)
**Last Updated:** 2026-05-28
