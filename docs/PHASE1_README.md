# Phase 1 MVP — Getting Started

## What You're Building

An MCP (Model Context Protocol) server that connects Claude to your Etsy shop. Phase 1 delivers 10 core operations for reading and managing your shop: listings, inventory, and orders.

**Key Facts:**
- 10 operations across 28 files
- 10 developers, 10 days (parallel execution)
- 181 tests, >85% coverage mandatory
- Straight-to-main Git workflow (10 commits)
- Complete thread-safety and security guarantees
- NIST SP 800-53 Rev. 5 compliance

---

## 5-File Reading Order

**Start here and read in this order:**

1. **This file** (PHASE1_README.md) — Overview and high-level orientation (5 min)
2. **PHASE1_QUICK_REFERENCE.md** — Daily developer guide, commands, templates (10 min)
3. **ETSY_MCP_PHASE1_IMPLEMENTATION_PLAN.md** — Detailed 10-day timeline with file specs (15 min)
4. **PHASE1_ARCHITECTURE_SPECIFICATION.md** — Deep-dive architecture, models, thread-safety (20 min)
5. **PHASE1_SECURITY_AND_NIST_MAPPING.md** — Security, threats, compliance, controls (15 min)

**Total reading time:** ~65 minutes. Worth every second to understand the full system.

---

## 10-Day Timeline at a Glance

| Day | Developer | Track | Deliverables | Files | Tests |
|-----|-----------|-------|--------------|-------|-------|
| 1 | Dev-A | Foundation | Base classes, registry, config, models | 8 | 23 |
| 2 | Dev-B | P1-Read-A | Get shop, list listings, get listing | 3 | 15 |
| 3 | Dev-C | P1-Read-B | Get inventory, list orders, get order | 3 | 15 |
| 4 | Dev-D | Integration-A | Validate P1 reads, fix issues | 3 | 18 |
| 5 | Dev-G | P2-Write-A | Create listing, update listing | 3 | 18 |
| 6 | Dev-H | P2-Write-B | Deactivate listing, additional op | 2 | 12 |
| 7 | Dev-I | P2-Write-C | Approve order, update order status | 2 | 12 |
| 8 | Dev-J | Infrastructure | Orchestration, rate limiting | 1 | 6 |
| 9 | Dev-K | Integration-B | Full integration tests | 2 | 12 |
| 10 | Dev-K | Finalization | Final verification, deployment ready | 1 | 6 |
| **TOTAL** | | | | **28** | **181** |

---

## 3-Pillar Architecture

Every operation follows this structure:

```
┌─────────────────────────────────┐
│         CLI Layer               │
│  (routing, input validation)    │
└────────────────┬────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   ┌─────────────┐   ┌──────────────┐
   │   Config    │   │  Guardrails  │
   │  (4-level)  │   │ (safety, ops)│
   └─────────────┘   └──────────────┘
```

**Each pillar is independent:**
- Config: Environment variables → Repo config → Master config → Code defaults
- Guardrails: Rate limits, approval gates, operation status tracking
- CLI: Routes commands, validates input, returns operation responses

---

## Developer Track Assignments

**10 developers, 10 independent tracks, zero file conflicts:**

- **Dev-A** (Day 1): Foundation only — no dependencies
- **Dev-B** (Days 2-3): P1 Read-A — waits for Dev-A, independent from Dev-C
- **Dev-C** (Days 2-3): P1 Read-B — waits for Dev-A, independent from Dev-B
- **Dev-D** (Day 4): Integration-A — integrates B+C outputs
- **Dev-G** (Day 5): P2 Write-A — starts write operations
- **Dev-H** (Days 6-7): P2 Write-B — parallel with Dev-I
- **Dev-I** (Days 6-7): P2 Write-C — parallel with Dev-H
- **Dev-J** (Day 8): Infrastructure — adds orchestration
- **Dev-K** (Days 9-10): Integration-B + Finalization — comprehensive testing

**Parallelization Strategy:**
- Days 2-3: Dev-B and Dev-C work in parallel (zero file overlap)
- Days 6-8: Dev-H, Dev-I, Dev-J work in parallel (zero file overlap)
- Result: 10 developers can commit simultaneously, zero merge conflicts

---

## Git Workflow

**Straight-to-main, frequent commits:**

```bash
# Create feature branch (optional)
git checkout -b feature/my-operation

# Make changes, test, verify
make check        # All quality gates must pass

# Commit with clear message
git commit -m "feat: Implement my operation"

# Push to main
git push origin feature/my-operation

# Or commit directly to main (allowed in this project)
git commit -m "feat: Implement my operation"
git push origin main
```

**Commit Prefixes:**
- `feat:` — New operation or feature
- `test:` — New tests or test improvements
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code refactoring

---

## Quality Gate (6-Point Check)

Before EVERY commit, run:

```bash
make check    # Runs all 6 checks in sequence
```

**The 6 checks (in order):**

1. **Tests** — All 181 tests must pass
   ```bash
   make test
   ```

2. **Coverage** — Must be >= 85%
   ```bash
   make coverage
   ```

3. **Lint** — No style violations (ruff)
   ```bash
   make lint
   ```

4. **Format** — Consistent code style (black)
   ```bash
   make format
   ```

5. **Type Check** — Type safety (mypy --strict)
   ```bash
   make type-check
   ```

6. **Security** — No hardcoded secrets (bandit)
   ```bash
   make security
   ```

**Rule**: If ANY check fails, fix it before pushing. Only push when ALL checks pass.

---

## Daily Rituals

### 10 AM Stand-up

```bash
# What changed since yesterday?
git log --oneline main --since="yesterday"

# Current status?
git status

# Last GitHub Actions run?
gh run list --limit 1
```

### 4 PM Progress Report

```bash
# Commits made today
git log --oneline main --since="today"

# Tests added
make test

# Coverage maintained?
make coverage | grep "^TOTAL"
```

### 5 PM Lead Review

```bash
# Final verification
git status
make check
make coverage
```

---

## Thread-Safety Guarantees

All of these are guaranteed by the architecture:

- ✓ **OperationRegistry RLock** — Thread-safe concurrent registration (10+ developers)
- ✓ **MockEtsyAPI Fixed Data** — LISTING_IDS=[101,102,103], ORDER_IDS=[201,202] (immutable)
- ✓ **Config Hierarchy + RLock** — Thread-safe caching with LRU
- ✓ **SQLite WAL Mode** — Concurrent readers + single writer
- ✓ **Rate Limiter Atomic** — Token bucket operations are atomic
- ✓ **Test Isolation by PID** — Each test gets its own temp database

**Result:** 10 developers can work in parallel with zero race conditions, zero merge conflicts, zero coordination overhead.

---

## Security: 4 Critical Rules

**Enforce always, no exceptions:**

1. **No hardcoded secrets**
   - Use Config.get() for all credentials
   - Never write API keys in code

2. **Never log secrets**
   - Redaction filter auto-removes api_key, token, password, etc.
   - Use setup_logger_with_redaction() in all modules

3. **Approval gates for WRITE**
   - All 4 WRITE operations require explicit user approval
   - Gate has 1-hour TTL, status tracking, approval/rejection

4. **TLS 1.3 enforced**
   - All Etsy API calls use TLS 1.3 minimum/maximum
   - No downgrade, no older versions allowed

**Additional Standards:**
- NIST SP 800-53 Rev. 5 compliance (13 controls)
- AES-256-GCM encryption for credentials
- PBKDF2-SHA256 key derivation (600,000 iterations)
- HMAC-SHA256 audit log signatures

---

## Testing Strategy

**181 tests total, >85% coverage mandatory:**

| Area | Tests | Coverage Target |
|------|-------|-----------------|
| MockEtsyAPI | 11 | 95%+ |
| Config | 12 | 95%+ |
| Registry | 8 | 95%+ |
| Operation Models | 15 | 95%+ |
| P1 Read-A | 15 | 90%+ |
| P1 Read-B | 15 | 90%+ |
| P2 Write-A | 18 | 90%+ |
| P2 Write-B | 12 | 90%+ |
| P2 Write-C | 12 | 90%+ |
| Infrastructure | 6 | 85%+ |
| Integration | 12 | 85%+ |
| **TOTAL** | **181** | **>85%** |

**Testing Patterns:**
- Unit tests for each operation (properties, validation, execution, schema)
- Integration tests for workflows (read → write → verify)
- Edge case tests (approval gate expiry, rate limit exceeded, validation failures)
- Thread-safety tests (concurrent registration, config access, logging)

---

## File Organization

Complete directory structure after Phase 1:

```
etsy-mcp/
├── .claude/
│   ├── ETSY_MCP_PHASE1_IMPLEMENTATION_PLAN.md
│   ├── PHASE1_QUICK_REFERENCE.md
│   └── etsy-mcp.json (example config)
├── .github/
│   └── workflows/
│       └── test.yml (CI/CD pipeline)
├── src/
│   ├── __init__.py
│   ├── base_operation.py (BaseOperationDef, WriteOperationDef)
│   ├── registry.py (OperationRegistry, REGISTRY instance)
│   ├── config.py (Config hierarchy, caching)
│   ├── operation_models.py (OperationStatus, ApprovalGate, OperationRequest)
│   ├── operations/
│   │   ├── p1_read_a/ (Dev-B: shop, listings, listing)
│   │   ├── p1_read_b/ (Dev-C: inventory, orders)
│   │   ├── p2_write_a/ (Dev-G: create, update listings)
│   │   ├── p2_write_b/ (Dev-H: deactivate, etc.)
│   │   ├── p2_write_c/ (Dev-I: approve, update orders)
│   │   └── infrastructure/ (Dev-J: orchestration)
│   ├── utils/
│   │   └── logging.py (setup_logger_with_redaction)
│   └── cli.py (MCP CLI handler)
├── tests/
│   ├── fixtures/
│   │   └── mock_etsy_api.py (MockEtsyAPI, FIXED data)
│   ├── test_*.py (Individual operation tests)
│   └── integration/
│       └── test_workflows.py (End-to-end tests)
├── docs/
│   ├── PHASE1_README.md (this file)
│   ├── PHASE1_ARCHITECTURE_SPECIFICATION.md
│   └── PHASE1_SECURITY_AND_NIST_MAPPING.md
├── Makefile (check, test, coverage, lint, format, type-check, security)
├── pyproject.toml (project config, dependencies)
├── poetry.lock (locked dependencies)
└── README.md (main project README)
```

---

## Success Criteria (10-Point Checklist)

✓ Day 1: Foundation architecture deployed, all 23 tests passing  
✓ Day 3: All P1 Read operations deployed, 53 tests passing  
✓ Day 4: Integration validation complete, zero conflicts  
✓ Day 5: P2 Write foundation deployed, approval gates working  
✓ Day 8: All write operations complete, 100+ tests passing  
✓ Day 9-10: Integration tests comprehensive, 181 tests passing  
✓ Coverage: >= 85% across all modules  
✓ Quality: All 6 checks pass (lint, format, type, security, tests, coverage)  
✓ Security: 4 critical rules enforced, no secrets in code/logs  
✓ Deployment Ready: 10 commits to main, zero pending changes  

---

## FAQ & Troubleshooting

**Q: What if I'm blocked on another developer's work?**
- A: Parallelization is designed to prevent this. If blocked, check the dependency table in PHASE1_IMPLEMENTATION_PLAN.md.

**Q: Can I commit directly to main or do I need a PR?**
- A: Straight-to-main workflow is allowed. No PRs required. Commit directly if all checks pass.

**Q: What if `make check` fails?**
- A: Fix the failing check (lint, format, type-check, security, tests, or coverage) and re-run. See PHASE1_QUICK_REFERENCE.md troubleshooting section.

**Q: How do I handle merge conflicts with 10 developers?**
- A: You shouldn't have any. Parallelization strategy ensures zero file overlap. If you do have conflicts, something is wrong — check you're working on the right day's files.

**Q: Can I work ahead on the next day's tasks?**
- A: Only if your track is ready. Check Day-Specific Dependencies table.

**Q: What's the approval gate workflow exactly?**
- A: Developer creates gate → User reviews → User approves/rejects → Operation verifies gate is APPROVED and not expired before executing. Full details in PHASE1_ARCHITECTURE_SPECIFICATION.md.

**Q: Do I need to push immediately or can I batch commits?**
- A: Frequency depends on your schedule. The plan assumes daily commits (one per developer per day). You can batch if needed, just maintain the overall 10-commit schedule.

**Q: Where's the Etsy API documentation?**
- A: MockEtsyAPI in tests/fixtures/mock_etsy_api.py shows all response structures. In production, use official Etsy API docs.

---

## Next Steps

### If You're Dev-A (Day 1)

1. Read all 5 files (65 min)
2. Read ETSY_MCP_PHASE1_IMPLEMENTATION_PLAN.md Day 1 section (20 min)
3. Read PHASE1_QUICK_REFERENCE.md operation template (10 min)
4. Create 8 foundation files (as specified in IMPLEMENTATION_PLAN)
5. Run `make check` (must all pass)
6. Commit: `git commit -m "feat: Implement Phase 1 MVP foundation architecture"`
7. Push: `git push origin main`
8. Notify other developers: Day 1 foundation ready ✓

### If You're Dev-B or Dev-C (Days 2-3)

1. Wait for Dev-A to push Day 1 (check GitHub)
2. Pull latest: `git pull origin main`
3. Read your day's section in IMPLEMENTATION_PLAN
4. Create 3 operations as specified
5. Write tests (see template in QUICK_REFERENCE)
6. Run `make check` (must all pass)
7. Commit and push to main
8. Notify lead: Day 2 or 3 complete ✓

### If You're Dev-D (Day 4)

1. Wait for Dev-B and Dev-C to push (check GitHub)
2. Pull latest: `git pull origin main`
3. Read integration section in IMPLEMENTATION_PLAN
4. Create integration tests and validators
5. Run `make check` (must all pass)
6. Commit and push
7. Verify no regressions: `make test`

### For All Developers

1. **Morning (10 AM)**: Run stand-up commands
2. **During Day**: Code, test, make sure `make check` passes
3. **Before Push**: Final `make check` verification
4. **After Push**: Update progress report
5. **Evening (5 PM)**: Lead review and verification

---

## Contacts & Resources

- **Architecture Questions**: See PHASE1_ARCHITECTURE_SPECIFICATION.md
- **Security/Compliance**: See PHASE1_SECURITY_AND_NIST_MAPPING.md
- **Daily Guidance**: See PHASE1_QUICK_REFERENCE.md
- **Detailed Timeline**: See ETSY_MCP_PHASE1_IMPLEMENTATION_PLAN.md
- **Config Issues**: Config hierarchy explained in PHASE1_ARCHITECTURE_SPECIFICATION.md
- **Test Problems**: Test patterns in PHASE1_QUICK_REFERENCE.md
- **Approval Gates**: Full workflow in PHASE1_ARCHITECTURE_SPECIFICATION.md

---

## You're Ready

You have everything needed to build this successfully:
- Clear timeline (10 days, 10 commits)
- Zero merge conflicts (parallelization strategy)
- Complete architecture (3 pillars, fully documented)
- Security guarantees (4 critical rules, NIST compliance)
- Quality standards (6-point gate, >85% coverage)
- Daily structure (stand-ups, reports, reviews)

**The next step depends on which day you're starting:**

- **If Dev-A**: Start Day 1 foundation
- **If Dev-B/C**: Wait for Day 1, then start Day 2/3
- **If Dev-D+**: Follow Day-Specific Dependencies

**When in doubt, reference PHASE1_QUICK_REFERENCE.md for templates and commands.**

Ready to build? Let's go. 🚀
