# Phase 1 Quick Reference — Daily Developer Guide

## Daily Checklist

### Morning (10 AM Stand-up)
```bash
# Check what changed since yesterday
git log --oneline -5 main

# Check GitHub Actions status
gh run list --limit 5

# Check current coverage
make coverage
```

### During Development
- Create local feature branch
- Implement operation or test
- Run `make check` before every commit
- Commit with message: `feat: <description>` or `test: <description>`
- Push to main (straight-to-main workflow)

### Evening (5 PM Review)
```bash
# Verify no regressions
git status
make check
make coverage

# Review commits pushed today
git log --oneline main -5
```

---

## File Creation Templates

### Operation Class Template

```python
from src.base_operation import BaseOperationDef
from src.operation_models import ValidationResult

class MyOperation(BaseOperationDef):
    @property
    def name(self) -> str:
        return "my_operation"
    
    @property
    def operation_type(self) -> str:
        return "READ"  # or "WRITE", "BULK", "ORCHESTRATED"
    
    @property
    def rate_limit(self) -> int:
        return 50  # per minute
    
    @property
    def requires_approval(self) -> bool:
        return False  # True for WRITE operations
    
    def validate(self, arguments: Dict[str, Any]) -> ValidationResult:
        if "required_key" not in arguments:
            return {"valid": False, "reason": "missing required_key"}
        return {"valid": True, "reason": None}
    
    def execute(self, arguments: Dict[str, Any], approval_gate=None) -> Dict[str, Any]:
        # For WRITE operations: validate approval_gate
        if self.requires_approval:
            if approval_gate is None or approval_gate.status != "APPROVED" or approval_gate.is_expired():
                return {"status": "FAILED", "error": "Approval required"}
        
        # Implement operation logic
        return {
            "status": "COMPLETED",
            "operation_name": self.name,
            "data": {"result": "success"}
        }
    
    def get_tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Description of operation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "required_key": {"type": "string"}
                },
                "required": ["required_key"]
            }
        }
```

### Test Class Template

```python
import pytest
from src.operations.my_operation import MyOperation
from src.operation_models import ApprovalGate, OperationStatus

@pytest.fixture
def operation():
    return MyOperation()

@pytest.fixture
def approval_gate():
    gate = ApprovalGate()
    gate.approve()
    return gate

class TestMyOperation:
    def test_name(self, operation):
        assert operation.name == "my_operation"
    
    def test_operation_type(self, operation):
        assert operation.operation_type == "READ"
    
    def test_requires_approval(self, operation):
        assert operation.requires_approval is False
    
    def test_rate_limit(self, operation):
        assert operation.rate_limit == 50
    
    def test_validate_success(self, operation):
        result = operation.validate({"required_key": "value"})
        assert result["valid"] is True
    
    def test_validate_failure(self, operation):
        result = operation.validate({})
        assert result["valid"] is False
        assert "required_key" in result["reason"]
    
    def test_execute_success(self, operation):
        response = operation.execute({"required_key": "value"})
        assert response["status"] == "COMPLETED"
        assert response["operation_name"] == "my_operation"
    
    def test_get_tool_schema(self, operation):
        schema = operation.get_tool_schema()
        assert "name" in schema
        assert "inputSchema" in schema
        assert schema["name"] == "my_operation"
```

---

## Quality Gate Commands

Run before EVERY commit:

```bash
# Run all checks (recommended)
make check

# Or run individually:
make test         # pytest - all tests must pass
make coverage     # >= 85% required
make lint         # ruff - no violations
make format       # black - consistent style
make type-check   # mypy --strict - type safety
make security     # bandit - no hardcoded secrets
```

**Status**: Only push when ALL checks pass.

---

## Git Workflow

### Create and Commit
```bash
# Create feature branch locally (optional, can work on main)
git checkout -b feature/my-feature

# Make changes
# Edit src/ and tests/

# Verify quality
make check

# Commit with clear message
git commit -m "feat: Implement my new operation"
# or
git commit -m "test: Add tests for my operation"

# Push to main
git push origin feature/my-feature  # or directly to main
```

### Commit Message Prefixes
- `feat:` — New feature (operation, command, etc.)
- `test:` — New tests or test improvements
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code refactoring
- `perf:` — Performance improvements

---

## Configuration

### 4-Level Priority (Highest to Lowest)

1. **Environment Variables** (highest priority)
   ```bash
   export ETSY_MCP_API_KEY="your-key"
   export ETSY_MCP_RATE_LIMIT="100"
   ```

2. **Repo Config** (`.claude/etsy-mcp.json`)
   ```json
   {
     "api_key": "from-repo",
     "rate_limit": 50
   }
   ```

3. **Master Config** (`~/.claude/etsy-mcp.json`)
   ```json
   {
     "api_key": "from-home",
     "rate_limit": 40
   }
   ```

4. **Code Defaults** (lowest priority)
   ```python
   DEFAULTS = {
     "api_key": None,
     "rate_limit": 50
   }
   ```

### Using Config in Code

```python
from src.config import Config

# Config.get() handles all 4 levels automatically
api_key = Config.get("api_key")  # Returns highest priority value
rate_limit = Config.get("rate_limit", 50)  # Default if not found
```

---

## Thread-Safety Rules

**ALWAYS follow these patterns:**

1. **Use Config.get()** — not direct env access
   ```python
   # ✓ CORRECT
   api_key = Config.get("api_key")
   
   # ✗ WRONG
   api_key = os.environ.get("ETSY_MCP_API_KEY")
   ```

2. **Use REGISTRY for operation access**
   ```python
   # ✓ CORRECT
   from src.registry import REGISTRY
   op = REGISTRY.get("my_operation")
   
   # ✗ WRONG - don't create new instances
   op = MyOperation()
   ```

3. **Use MockEtsyAPI (immutable fixtures)**
   ```python
   # ✓ CORRECT - FIXED_IDS never change
   LISTING_IDS = [101, 102, 103]
   ORDER_IDS = [201, 202]
   
   # ✗ WRONG - don't modify mock data
   mock_api.LISTING_IDS.append(104)
   ```

4. **Test isolation by PID**
   ```python
   # ✓ CORRECT - each test gets its own database
   db_path = f"tests/fixtures/test_{os.getpid()}.db"
   
   # ✗ WRONG - don't share databases between tests
   db_path = "tests/fixtures/test.db"
   ```

5. **Never modify shared state**
   - Don't update global registries in tests
   - Don't modify fixture data
   - Don't create new REGISTRY instances

---

## MockEtsyAPI Fixtures (FIXED AND IMMUTABLE)

These values are hardcoded and never change across all tests:

```python
LISTING_IDS = [101, 102, 103]      # Always these 3
ORDER_IDS = [201, 202]              # Always these 2

# Example responses (FIXED):
{
    "listing_id": 101,
    "title": "Horror Mask",
    "description": "Scary but stylish",
    "price": 2999,  # in cents
    "quantity": 5,
    "state": "active"
}

{
    "order_id": 201,
    "seller_user_id": 123,
    "buyer_user_id": 456,
    "creation_tsz": 1609459200,
    "status": "completed"
}
```

---

## Logging & Redaction

### Setup in Your Code

```python
from src.utils.logging import setup_logger_with_redaction

logger = setup_logger_with_redaction(__name__)

# These are automatically redacted in logs:
logger.info(f"API Key: {api_key}")  # Logs: "API Key: [REDACTED]"
logger.error(f"Token: {token}")      # Logs: "Token: [REDACTED]"
logger.debug(f"Password: {pwd}")     # Logs: "Password: [REDACTED]"
```

### Redacted Fields

Automatically removed from ALL log output:
- `api_key`, `api_secret`
- `password`, `passwd`, `pwd`
- `token`, `access_token`, `refresh_token`
- `client_secret`, `secret`
- `authorization`, `x-api-key`

---

## Approval Gates (WRITE Operations Only)

### Request Approval

```python
from src.operation_models import ApprovalGate

# Developer creates gate
gate = ApprovalGate()
gate_id = gate.id

# User reviews and approves/rejects
if user_approved:
    gate.approve()  # status = "APPROVED"
else:
    gate.reject()   # status = "REJECTED"
```

### Execute with Gate

```python
response = operation.execute(arguments, approval_gate=gate)

# Gate validation in execute():
if approval_gate is None:
    return {"status": "FAILED", "error": "Approval required"}
if approval_gate.status != "APPROVED":
    return {"status": "FAILED", "error": "Not approved"}
if approval_gate.is_expired():  # TTL = 1 hour
    return {"status": "FAILED", "error": "Approval expired"}
```

### Example Workflow

```python
# Step 1: Developer calls WRITE operation
gate = ApprovalGate()  # TTL = 1 hour
operation_request = OperationRequest(
    operation_name="create_listing",
    arguments={"title": "Horror Mask"},
    operation_type="WRITE",
    approval_gate_id=gate.id
)

# Step 2: User reviews (in CLI)
print(f"Review: {operation_request}")
if user_confirms:
    gate.approve()

# Step 3: Execute
response = operation.execute(
    arguments=operation_request.arguments,
    approval_gate=gate
)
# Returns: {"status": "COMPLETED", "operation_name": "create_listing", ...}
```

---

## Operation Response Format

All operations return this structure:

```python
{
    "status": "COMPLETED",              # COMPLETED, FAILED, EXECUTING, etc.
    "operation_name": "my_operation",   # From operation.name
    "request_id": "uuid-here",          # Unique request ID
    "timestamp": "2026-05-29T10:30:00Z", # ISO 8601
    "data": {...},                      # Success: operation-specific data
    "error": None,                      # Failure: error message
    "approval_gate_id": "gate-id"       # For WRITE operations
}
```

---

## Common Errors & Fixes

### Error: Coverage < 85%

```bash
# Run coverage report
make coverage

# Shows which lines aren't tested
# Add tests for those lines
# Rerun: make coverage

# Common issues:
# - Not testing error cases
# - Not testing validation failures
# - Not testing approval gate expiry
```

### Error: Lint Fails

```bash
make lint      # See ruff violations
make format    # Auto-fix with black
make lint      # Verify fixed
```

### Error: Type Check Fails

```bash
make type-check

# Common issues:
# - Missing type hints on function args
# - Wrong type returned
# - None where value expected
# Fix: Add type hints or cast types
```

### Error: Security Scan Fails (Hardcoded Secrets)

```bash
make security  # Run bandit

# Common issues:
# - Hardcoded API keys
# - Passwords in code
# - Tokens in strings
# Fix: Use Config.get() for all credentials
```

### Error: Operation Not in Registry

```bash
# Make sure operation is registered
from src.registry import REGISTRY

# Option 1: Register in __init__.py
from src.operations.my_operation import MyOperation
REGISTRY.register(MyOperation())

# Option 2: Check it's actually registered
assert REGISTRY.get("my_operation") is not None
```

---

## Day-Specific Dependencies

| Day | Developer | Deliverables | Depends On |
|-----|-----------|--------------|-----------|
| 1 | Dev-A | Foundation (8 files) | Nothing — this is foundation |
| 2 | Dev-B | P1-A (3 files) | Dev-A files ready |
| 3 | Dev-C | P1-B (3 files) | Dev-A files ready |
| 4 | Dev-D | Integration (3 files) | Dev-B + Dev-C files |
| 5 | Dev-G | P2-Write-A (3 files) | Dev-D files |
| 6 | Dev-H | P2-Write-B (2 files) | Dev-G files |
| 7 | Dev-I | P2-Write-C (2 files) | Dev-G files |
| 8 | Dev-J | Infrastructure (1 file) | Dev-G files |
| 9 | Dev-K | Integration tests (2 files) | All prior files |
| 10 | Dev-K | Final verification (1 file) | All prior files |

---

## Daily Ritual Commands

### Stand-up (10 AM)

```bash
# What changed since yesterday?
git log --oneline main --since="yesterday"

# What's in progress?
git status

# Any failed tests?
gh run list --limit 1

# Coverage status?
make coverage | grep "^TOTAL"
```

### Progress Report (4 PM)

```bash
# Commits made today
git log --oneline main --since="today"

# Tests added
make test

# Coverage maintained?
make coverage | grep "^TOTAL"

# Any issues?
make check
```

### Lead Review (5 PM)

```bash
# Final verification
git status

# All quality gates pass?
make check

# Coverage still above 85%?
make coverage

# Ready to push?
git log --oneline -5
```

---

## File Organization

Expected structure after Phase 1:

```
etsy-mcp/
├── .claude/
│   ├── ETSY_MCP_PHASE1_IMPLEMENTATION_PLAN.md
│   ├── PHASE1_QUICK_REFERENCE.md
│   └── etsy-mcp.json (example)
├── .github/
│   └── workflows/
│       └── test.yml
├── src/
│   ├── __init__.py
│   ├── base_operation.py
│   ├── registry.py
│   ├── config.py
│   ├── operation_models.py
│   ├── operations/
│   │   ├── __init__.py
│   │   ├── p1_read_a/
│   │   │   ├── __init__.py
│   │   │   ├── operation1.py
│   │   │   ├── operation2.py
│   │   │   └── operation3.py
│   │   ├── p1_read_b/
│   │   │   ├── __init__.py
│   │   │   ├── operation4.py
│   │   │   ├── operation5.py
│   │   │   └── operation6.py
│   │   ├── p2_write_a/
│   │   │   ├── __init__.py
│   │   │   ├── create_listing.py
│   │   │   └── update_listing.py
│   │   ├── p2_write_b/
│   │   │   ├── __init__.py
│   │   │   ├── deactivate_listing.py
│   │   │   └── operation9.py
│   │   ├── p2_write_c/
│   │   │   ├── __init__.py
│   │   │   ├── approve_order.py
│   │   │   └── operation11.py
│   │   └── infrastructure/
│   │       ├── __init__.py
│   │       └── orchestration.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logging.py
│   └── cli.py
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── mock_etsy_api.py
│   ├── test_fixtures.py
│   ├── test_config.py
│   ├── test_registry.py
│   ├── test_operation_models.py
│   ├── test_p1_read_a.py
│   ├── test_p1_read_b.py
│   ├── test_p2_write_a.py
│   ├── test_p2_write_b.py
│   ├── test_p2_write_c.py
│   ├── test_infrastructure.py
│   └── integration/
│       ├── __init__.py
│       └── test_workflows.py
├── docs/
│   ├── PHASE1_README.md
│   ├── PHASE1_ARCHITECTURE_SPECIFICATION.md
│   └── PHASE1_SECURITY_AND_NIST_MAPPING.md
├── Makefile
├── pyproject.toml
├── poetry.lock
└── README.md
```

---

## Frequently Missed Items

- [ ] Did you add tests for your operation?
- [ ] Is coverage still > 85%?
- [ ] Did you test error cases and validation failures?
- [ ] Did you use Config.get() for all credentials?
- [ ] Did you register your operation in __init__.py?
- [ ] Did you run `make check` before committing?
- [ ] Did you verify `make coverage` >= 85%?
- [ ] Did approval gate tests cover all edge cases?
- [ ] Is your operation in the correct day's directory?
- [ ] Did you check for hardcoded secrets with bandit?

---

## Troubleshooting

**Q: "Operation not found" error**
- A: Check it's registered: `REGISTRY.get("my_operation")`
- A: Verify import in `__init__.py`

**Q: Tests pass locally but fail in CI**
- A: Check environment variables set correctly
- A: Verify test isolation (using temp databases by PID)
- A: Check for race conditions in concurrent tests

**Q: Coverage report shows < 85%**
- A: Run `make coverage` to see which lines untested
- A: Add tests for error cases
- A: Test approval gate expiry, rejection, validation failures

**Q: "make check" fails partway through**
- A: Run each step individually: `make lint`, `make format`, `make type-check`
- A: Fix issues in order: format → lint → type-check → security
- A: Rerun `make check` to verify all pass

**Q: How do I test approval gates?**
- A: Create gate, call approve(), verify status == "APPROVED"
- A: Test is_expired() after TTL
- A: Test execute() without gate fails

---

## Emergency Contacts

- **Architecture Questions**: See PHASE1_ARCHITECTURE_SPECIFICATION.md
- **Security Issues**: See PHASE1_SECURITY_AND_NIST_MAPPING.md
- **Parallel Dev Issues**: See ETSY_MCP_PHASE1_IMPLEMENTATION_PLAN.md (Day-Specific Dependencies)
- **Full Timeline**: See PHASE1_README.md (10-Day Timeline at a Glance)
