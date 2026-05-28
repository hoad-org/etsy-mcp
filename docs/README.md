# Etsy MCP Server — Documentation

This directory contains the complete design specification and implementation guide for the Etsy MCP (Model Context Protocol) server.

## Quick Links

- **[DESIGN.md](DESIGN.md)** — Complete production-ready specification (~6000 lines)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — 6-layer defense-in-depth architecture
- **[OPERATIONS.md](OPERATIONS.md)** — All 18 operations reference (P1-P4)
- **[MCP-COMPLIANCE.md](MCP-COMPLIANCE.md)** — MCP specification compliance checklist
- **[SECURITY.md](SECURITY.md)** — NIST SP 800-53 Rev. 5 controls alignment
- **[IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md)** — 8-week phased rollout

## Overview

The Etsy MCP server provides secure, audited access to Etsy shop management operations through the Model Context Protocol. It implements a 6-layer defense-in-depth security architecture with:

- **OAuth 2.1 PKCE** authorization code flow
- **JWT token validation** (8-step pipeline)
- **Rate limiting** per shop with circuit breaker protection
- **Approval gates** for write operations
- **Async queue processor** for long-running bulk operations
- **Immutable audit logging** with HMAC-SHA256 signatures
- **NIST SP 800-53 Rev. 5** compliance (13 controls mapped)

## Operations (18 Total)

### P1: Read-Only (Immediate, 50/min limit)
- `get_shop_info` — Shop details, rates, shipping, policies
- `list_listings` — Browse inventory with filters and pagination
- `get_listing` — Single listing details (price, inventory, images)
- `get_listing_inventory` — Current stock levels by SKU
- `list_orders` — Recent orders with status and filtering
- `get_order` — Single order details with shipping info

### P2: Write Operations (Approval Required, 5/min limit)
- `update_listing` — Modify listing fields (title, price, tags, shipping)
- `update_listing_inventory` — Update stock levels by SKU
- `publish_listing` — Activate draft listing to shop
- `deactivate_listing` — Temporarily disable listing
- `update_shop_info` — Shop policies, announcements, vacation mode

### P3: Bulk Operations (Async Batched, 5/min limit)
- `bulk_update_listings` — Update fields across multiple listings
- `bulk_update_inventory` — Sync inventory across multiple SKUs
- `bulk_publish_listings` — Activate multiple draft listings
- `bulk_deactivate_listings` — Disable multiple listings

### P4: Orchestrated (Step Functions, 1/5min limit)
- `archive_old_listings` — Auto-deactivate listings with no sales in 180+ days
- `seasonal_inventory_sync` — Automated inventory rebalancing from warehouse feed
- `bulk_price_adjustment` — Coordinated pricing across store for sales/promotions

## Architecture Layers

```
Layer 6: Orchestration & Integration (P4)
    ↓ AWS Step Functions, webhook callbacks
Layer 5: Operations Queue & State (Phase 1A)
    ↓ Operation store, async queue, state machine
Layer 4: Authorization Gates (P2)
    ↓ Confirmation requests, approval workflows
Layer 3: Execution Layer (P1 + P2 + P3)
    ↓ Tool execution, bulk batching, result aggregation
Layer 2: API Client & Guardrails
    ↓ Etsy API, rate limiting, circuit breaker, retry logic
Layer 1: Transport & Protocol
    ↓ STDIO + OAuth 2.1 PKCE, JWT validation, session management
```

## Key Features

### Security
- ✅ OAuth 2.1 with PKCE (authorization code flow)
- ✅ JWT token validation (8-step pipeline)
- ✅ AES-256-GCM encryption (NIST FIPS 140-3 approved)
- ✅ PBKDF2-SHA256 key derivation (600k iterations)
- ✅ TLS 1.3 enforced on all API calls
- ✅ HMAC-SHA256 audit log signatures (immutable)
- ✅ Rate limiting per shop with circuit breaker
- ✅ Confirmation gates for write operations

### Resilience
- ✅ Exponential backoff with jitter (max 3 retries)
- ✅ Circuit breaker pattern (CLOSED/OPEN/HALF_OPEN)
- ✅ Three-level timeout enforcement (session, per-operation, socket)
- ✅ Async queue processor with state persistence
- ✅ Automatic operation recovery on restart

### Compliance
- ✅ NIST SP 800-53 Rev. 5 (13 controls mapped)
- ✅ MCP specification compliant
- ✅ Complete audit trail (all operations logged)
- ✅ Deterministic secret redaction in logs
- ✅ >85% test coverage requirement

## Implementation Roadmap

8-week phased rollout from foundation to production:

| Phase | Week | Deliverables | Status |
|-------|------|--------------|--------|
| A | 1 | Foundation modules (operations, registry, store) | Planned |
| B | 1 | P1 Read operations (6 tools) | Planned |
| C | 2 | Phase 1A infrastructure (async queue) | Planned |
| D | 2 | P2 Write operations (5 tools) | Planned |
| E | 3 | P3 Bulk operations (4 tools) | Planned |
| F | 3 | P4 Orchestrated operations (3 tools) | Planned |
| G | 4 | Security & audit (comprehensive logging) | Planned |
| H | 4 | Testing & documentation (>85% coverage) | Planned |

## Getting Started

1. **Read the Design**: Start with [DESIGN.md](DESIGN.md) for complete overview
2. **Understand Architecture**: Review [ARCHITECTURE.md](ARCHITECTURE.md) for 6-layer defense
3. **Check Compliance**: Verify [MCP-COMPLIANCE.md](MCP-COMPLIANCE.md) and [SECURITY.md](SECURITY.md)
4. **Plan Implementation**: Follow [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md)

## Files in This Directory

```
docs/
├── README.md                    # This file (overview and navigation)
├── DESIGN.md                    # Complete design specification (6000+ lines)
├── ARCHITECTURE.md              # 6-layer architecture details
├── OPERATIONS.md                # All 18 operations reference
├── MCP-COMPLIANCE.md            # MCP spec compliance
├── SECURITY.md                  # NIST controls alignment
├── IMPLEMENTATION-PLAN.md       # 8-week phased rollout
└── THREAT_MODEL.md              # Threat analysis and mitigations
```

## Success Criteria

The server is production-ready when:

- ✅ All 18 operations implemented and tested (P1-P4)
- ✅ >85% test coverage across all modules
- ✅ All NIST controls implemented and verified
- ✅ Complete audit trail with HMAC signatures
- ✅ Rate limiting and circuit breaker active
- ✅ OAuth 2.1 PKCE flow validated
- ✅ All code quality tools passing (lint, type-check, format)
- ✅ User guide and API reference complete
- ✅ Etsy API credentials management verified
- ✅ AWS Step Functions integration tested
- ✅ SQLite persistence verified
- ✅ Async queue processor operational
- ✅ All error paths tested and documented

## Support

For implementation questions, refer to the comprehensive guides in this directory. Each document is self-contained and includes:
- Detailed explanations and rationale
- Code examples and implementation patterns
- Testing strategies and coverage requirements
- Security considerations and threat mitigations
- Deployment procedures and troubleshooting

---

**Status**: Production-ready design specification complete
**Version**: 1.0.0
**Last Updated**: 2026-05-28
**Maintainer**: Craig Hoad
