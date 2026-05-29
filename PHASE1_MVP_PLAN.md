# Etsy MCP Phase 1 MVP — Development Plan

**Status**: Ready to Execute  
**Target Completion**: 2 weeks (straight-to-main, daily pushes)  
**Final Outcome**: P1 read operations fully functional + Phase 1A async infrastructure  

---

## Overview

Phase 1 MVP focuses on getting **6 read-only operations working end-to-end** with the async queue processor and approval gate foundation. Every day produces a working, testable increment that ships to main.

**Guiding Principle**: Small, shippable pieces. Commit. Push. Validate. Repeat.

---

## MVP Scope

### What Ships in Phase 1
✅ **P1 Read Operations (6 tools)** - Immediate execution, no approval required
- `get_shop_info` — Shop details (rates, shipping, policies)
- `list_listings` — All listings with filters (status, tag, sort, pagination)
- `get_listing` — Single listing details
- `get_listing_inventory` — Current stock by SKU
- `list_orders` — Recent orders with filtering
- `get_order` — Single order details

✅ **Phase 1A Infrastructure** - Foundation for P2-P4
- Async queue processor (background worker)
- Operation store (SQLite persistence)
- Approval gate models (P2 foundation, not integrated yet)

✅ **Security Foundation**
- Rate limiting (50/min for read operations)
- Circuit breaker (5 failures / 60s)
- Audit logging (JSONL + HMAC)
- Crypto manager (AES-256-GCM)

### What's NOT in Phase 1 (Phase 2+)
❌ P2 Write operations (requires approval gates integration)
❌ P3 Bulk operations
❌ P4 AWS Step Functions
❌ Approval workflow UI
❌ Web Push notifications
❌ Full admin dashboard

---

## Development Strategy: Straight to Main

**No feature branches. Every increment ships directly to main.**

### Why This Works for MVP
1. **Forces small, testable pieces** — Can't hide complexity in long-lived branches
2. **Faster feedback** — Push → run tests → catch bugs immediately
3. **Continuous deployment ready** — Always have a working version on main
4. **Psychological momentum** — Visible progress with every commit

### Daily Ritual
```bash
# Morning: Pull latest
git pull

# Throughout day: Code → Test → Commit → Push (repeat 3-5 times)
# Each push should be:
#   - Single feature or fix
#   - All tests pass (>85% coverage)
#   - All quality checks pass (lint, type, security)
#   - Runs cleanly in isolation

# Evening: Verify end-to-end still works
make test
make coverage
```

---

## Day-by-Day Execution Plan (2-Week Sprint)

### **Week 1: Foundation + First 3 Operations**

#### Day 1 Monday: Setup & Test Infrastructure (1 commit)
**Target**: All test frameworks ready, CI/CD green  
**Commits**:
1. `test: Add comprehensive test fixtures and mocking infrastructure`
   - Mock Etsy API responses for all P1 operations
   - Test database with auto-cleanup
   - Fixture factories for operations, approval gates
   - CI/CD pipeline verification (GitHub Actions)

**Push to main**: ✅

---

#### Day 2 Tuesday: First Read Operation — get_shop_info (2 commits)
**Target**: First tool works end-to-end: MCP → API → response  
**Commits**:
1. `feat: Implement get_shop_info operation and handler`
   - GetShopInfoOperation class in tools/p1_read.py
   - Execute method calls etsy_api.get_shop()
   - Parameter validation (none required)
   - Response schema matching

2. `test: Add comprehensive tests for get_shop_info`
   - Happy path: valid response
   - Error path: API failure
   - Rate limit enforcement
   - Audit logging verification
   - Coverage: >85%

**Push to main**: ✅ (both commits in one push)

---

#### Day 3 Wednesday: Second Operation — list_listings (2 commits)
**Target**: Filtering and pagination working  
**Commits**:
1. `feat: Implement list_listings with filtering and pagination`
   - ListListingsOperation in tools/p1_read.py
   - Parameters: status, tag, sort, limit, offset
   - Validation: limit 1-100, offset ≥ 0
   - Call etsy_api.list_listings(filters, pagination)

2. `test: Comprehensive list_listings tests (filtering, pagination, edge cases)`
   - Valid filters (active, draft, sold_out)
   - Sorting (date, price, relevance)
   - Pagination boundaries
   - Rate limit (50/min respected)
   - Coverage: >85%

**Push to main**: ✅

---

#### Day 4 Thursday: Third Operation — get_listing (2 commits)
**Target**: Detailed product data retrieval  
**Commits**:
1. `feat: Implement get_listing operation`
   - GetListingOperation in tools/p1_read.py
   - Parameter: listing_id (required, integer)
   - Response: full listing details (title, description, price, images, tags, inventory)
   - Validation: listing_id > 0

2. `test: Comprehensive get_listing tests`
   - Valid listing retrieval
   - Nonexistent listing (404 handling)
   - Response schema validation
   - Audit log verification
   - Coverage: >85%

**Push to main**: ✅

---

#### Day 5 Friday: End-to-End Validation (1 commit)
**Target**: All 3 operations work together, stress tested  
**Commits**:
1. `test: Integration tests for P1 read operations (workflow validation)`
   - Flow: list_listings → get_listing → get_listing_inventory (prepare for next op)
   - Rate limiting holds across operations
   - Circuit breaker triggers and resets
   - Audit trail complete for full workflow
   - Add performance benchmark (target: <200ms per operation)

**Push to main**: ✅

**Friday EOD Checkpoint**:
```bash
✅ 3 operations working end-to-end
✅ All tests passing (>85% coverage)
✅ All quality checks pass (lint, type, security)
✅ Audit logging complete
✅ Rate limiting verified
✅ Ready for weekend
```

---

### **Week 2: Complete P1 (3 More Operations) + Phase 1A Infrastructure**

#### Day 6 Monday: Fourth Operation — get_listing_inventory (2 commits)
**Target**: Inventory tracking ready  
**Commits**:
1. `feat: Implement get_listing_inventory operation`
   - GetListingInventoryOperation in tools/p1_read.py
   - Parameter: listing_id
   - Response: inventory by SKU (sku, quantity, is_available)
   - Handles products with variations

2. `test: Complete get_listing_inventory test suite`
   - Single SKU inventory
   - Multiple SKU variations
   - Out-of-stock handling
   - Audit logging
   - Coverage: >85%

**Push to main**: ✅

---

#### Day 7 Tuesday: Fifth Operation — list_orders (2 commits)
**Target**: Order management operations begin  
**Commits**:
1. `feat: Implement list_orders operation`
   - ListOrdersOperation in tools/p1_read.py
   - Parameters: status filter, date range, limit, offset
   - Response: orders with buyer info, items, shipping
   - Validation: status in (pending, processing, shipped, complete, cancelled)

2. `test: Complete list_orders test suite`
   - Status filtering
   - Date range filtering
   - Pagination
   - Response schema validation
   - Coverage: >85%

**Push to main**: ✅

---

#### Day 8 Wednesday: Sixth Operation — get_order (2 commits)
**Target**: All P1 read operations complete  
**Commits**:
1. `feat: Implement get_order operation`
   - GetOrderOperation in tools/p1_read.py
   - Parameter: order_id
   - Response: complete order details (items, shipping, buyer, status timeline)
   - Handle order states

2. `test: Complete get_order test suite`
   - Valid order retrieval
   - Order state transitions
   - Shipping info presence
   - Buyer PII handling (audit redaction)
   - Coverage: >85%

**Push to main**: ✅

---

#### Day 9 Thursday: Phase 1A Foundation — Operation Store (2 commits)
**Target**: Persistence layer ready for async execution  
**Commits**:
1. `feat: Implement OperationStore (SQLite persistence)`
   - Create schema: operations, approval_gates tables
   - CRUD operations for OperationRequest
   - State machine enforcement (PENDING → EXECUTING → COMPLETED/FAILED)
   - Queries for pending operations, expired approvals
   - Clean up old operations (TTL enforcement)

2. `test: Comprehensive OperationStore tests`
   - Table creation
   - State transitions (all valid paths)
   - Data persistence across sessions
   - TTL expiry
   - Query results validation
   - Coverage: >85%

**Push to main**: ✅

---

#### Day 10 Friday: Phase 1A Foundation — Async Queue Processor (2 commits)
**Target**: Background execution ready, P2 waiting for approval gates  
**Commits**:
1. `feat: Implement OperationQueue async processor`
   - Fetch pending operations from store
   - Execute via operation registry
   - Retry logic: exponential backoff (2^n * 1s, max 3)
   - State transitions (PENDING → EXECUTING → COMPLETED/FAILED)
   - Error handling and recovery

2. `test: Comprehensive OperationQueue tests`
   - Operation execution flow
   - Retry logic with exponential backoff
   - State machine transitions
   - Error handling (API failure, timeout, unknown op)
   - Concurrent operation safety
   - Coverage: >85%

**Push to main**: ✅

**Week 2 EOD Checkpoint**:
```bash
✅ All 6 P1 read operations working
✅ Phase 1A async queue ready
✅ SQLite persistence verified
✅ >85% coverage across all code
✅ All quality checks passing
✅ Ready for Phase 2
```

---

## Testing & Quality Gate for Each Commit

**Before pushing every commit:**

```bash
# 1. Run all tests
make test

# 2. Check coverage (must be >85%)
make coverage

# 3. Run linter
make lint

# 4. Check types
make type-check

# 5. Security scan
bandit -r src/

# 6. All pass? Push
git push
```

**Fail?** → Fix locally → Test again → Push. No broken main ever.

---

## Daily Standup Template

Each day EOD, document:

```markdown
## Day X - YYYY-MM-DD

### Completed
- [ ] Operation X implemented + tested
- [ ] All tests pass (>85% coverage)
- [ ] Quality checks pass
- [ ] Pushed to main

### Commits Pushed
1. `hash` - Commit message
2. `hash` - Commit message

### Next Day
- Operation Y implementation
- Operation Z testing
```

---

## MVP Success Criteria

**By end of Week 2, Phase 1 MVP is complete when:**

✅ All 6 P1 read operations implemented and tested  
✅ >85% test coverage across entire codebase  
✅ All quality checks passing (lint, type, security)  
✅ Async queue processor working  
✅ SQLite persistence verified  
✅ Audit logging complete for all operations  
✅ Rate limiting enforced (50/min)  
✅ Circuit breaker tested  
✅ No broken commits on main  
✅ Ready to onboard users for testing  

---

## Phase 1 → Phase 2 Transition

Once MVP is complete (Week 2 Friday):

### Phase 2 Planning (Week 3)
- Implement approval gates (P2 foundation → full integration)
- Add P2 write operations (5 operations)
- End-to-end approve → execute workflow
- Target: 2 more weeks

### Potential Phase 2 Operations
- `update_listing` — Modify listing fields
- `update_listing_inventory` — Update stock
- `publish_listing` — Activate draft
- `deactivate_listing` — Disable listing
- `update_shop_info` — Shop policies

---

## Risk Mitigation

### Risk: Code Quality Degrades
**Mitigation**: Quality gates non-negotiable. Every commit passes all checks. No exceptions.

### Risk: Bugs Accumulate
**Mitigation**: >85% test coverage required. Integration tests validate workflows.

### Risk: Scope Creep
**Mitigation**: P2, P3, P4 explicitly NOT in Phase 1. Stay focused on MVP.

### Risk: API Rate Limiting
**Mitigation**: Mock Etsy API in tests. Real API calls only in staging. Circuit breaker protects main.

---

## Deployment

### Development
- Local: `python -m src.server`
- Tests: `make test`
- Quality: `make check`

### Staging (Week 2 Thursday)
- Deploy main to staging environment
- Real Etsy API credentials (encrypted)
- Monitor audit logs for issues
- Load test rate limiting

### Production (Week 2 Friday)
- Deploy main to production
- Readonly access only (P1 operations)
- Full audit logging enabled
- Monitor error rates and latency

---

## Commit Message Format

Every commit follows pattern:

```
<type>(<scope>): <subject>

<body (optional)>

- Bullet point 1
- Bullet point 2

Closes: JIRA-XXX (if applicable)
```

**Types**: `feat`, `test`, `refactor`, `fix`, `docs`, `chore`

**Examples**:
- `feat(p1): Implement get_shop_info operation`
- `test(p1): Add comprehensive get_shop_info tests`
- `test(queue): Add OperationQueue retry logic tests`

---

## Tools & Dependencies

**Required** (pre-installed):
- Python 3.11+
- Poetry (dependency management)
- pytest (testing)
- mypy (type checking)
- ruff (linting)
- bandit (security)

**Check setup**:
```bash
make check
```

---

## Daily Pushes Metric

**Phase 1 Target**: 15-20 commits over 10 days

- Day 1: 1 commit
- Days 2-9: 2-3 commits each (16-18 commits)
- Day 10: 2 commits
- **Total**: ~19 commits to main

**Velocity**: Roughly 2-3 commits per developer per day. Multiple developers can work in parallel (different operations).

---

## Success Metrics (End of Phase 1)

| Metric | Target | Status |
|--------|--------|--------|
| P1 operations complete | 6/6 | Pending |
| Test coverage | >85% | Pending |
| Quality gates passing | 100% | Pending |
| Commits to main | 15-20 | Pending |
| Days to complete | 10 | Pending |
| Production ready | Yes | Pending |

---

## Next: Assign Developers & Start Day 1

Once this plan is approved:

1. **Day 1 kickoff**: Run test infrastructure setup
2. **Parallel tracks**: Developers can work on different operations simultaneously (no conflicts)
3. **Daily syncs**: 15-min standup, discuss blockers
4. **Continuous integration**: GitHub Actions validates every push
5. **Weekly demo**: Show working increment to stakeholders

**Ready to start? Pick a developer and begin Day 1.**

---

**Version**: 1.0.0  
**Created**: 2026-05-28  
**Status**: Ready to Execute
