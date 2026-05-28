# Etsy MCP - Secure Etsy Store Management

A production-grade Model Context Protocol (MCP) for secure Etsy store management with NIST-aligned security architecture.

## Features

**P1 (Current):** Read-only Etsy operations with enterprise-grade security
- `get_shop_info` — Get shop information
- `list_products` — List products with pagination
- `get_product` — Get product details
- `list_orders` — List recent orders

## Security

This MCP implements a 5-layer defense-in-depth architecture:

1. **Input Boundary** — CLI validation, rate limit checks
2. **Authorization** — RBAC roles, confirmation gates
3. **Credential Management** — AES-256-GCM encryption, PBKDF2 key derivation
4. **API Execution** — TLS 1.3+, certificate pinning, request signing
5. **Output Boundary** — Immutable audit log, cryptographic signing

See [SECURITY.md](SECURITY.md) for full details.

## Installation

```bash
git clone https://github.com/hoad-org/etsy-mcp.git
cd etsy-mcp
make dev
```

## Configuration

**Required environment variables:**
```bash
export ETSY_API_KEY="<your-encrypted-api-key>"
export ETSY_SHOP_ID="<your-shop-id>"
export ETSY_VAULT_PASSWORD="<strong-password>"
```

Configuration hierarchy (highest priority wins):
1. Environment variables
2. Repo config (`.etsy-mcp/config.json`)
3. Master config (`~/.etsy-mcp/config.json`)
4. Code defaults

## Usage

```bash
# Start MCP server
python -m src.server

# In Claude, use these tools:
# - get_shop_info()
# - list_products(status="active", limit=20, offset=0)
# - get_product(listing_id=123456)
# - list_orders(limit=20, offset=0)
```

## Testing

```bash
make test          # Run tests
make coverage      # Coverage report
make check         # All checks (lint, type-check, security)
```

**Coverage requirement:** >85% (non-negotiable for release)

## Development

**Code quality tools:**
- `ruff` — Linting
- `black` — Formatting
- `mypy --strict` — Type checking
- `bandit` — Security scanning

All must pass before commit:
```bash
make check
```

## Roadmap

- **P1** — Read-only MCP (in progress)
- **P2** — Design system + Canva integration
- **P3** — Product storage + metadata table
- **P4** — Live publishing

## License

MIT
