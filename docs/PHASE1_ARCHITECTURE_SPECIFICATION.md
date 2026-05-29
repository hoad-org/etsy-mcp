# Phase 1 Architecture Specification

## Overview

The Etsy MCP server follows a **3-pillar architecture** where each pillar is independent and testable in isolation. This document specifies the complete design, data models, thread-safety patterns, and implementation details.

---

## 3-Pillar Architecture

```
┌──────────────────────────────────────┐
│          CLI Layer                   │
│  (MCP routing, command handling)     │
│  Validates input, routes to          │
│  operations, formats responses       │
└─────────────────┬────────────────────┘
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
   ┌─────────────────┐  ┌──────────────┐
   │ Config Layer    │  │ Guardrails   │
   │ (4-level)       │  │ (rate limit, │
   │ (ENV → repo →   │  │  approval)   │
   │  home → code)   │  │              │
   └─────────────────┘  └──────────────┘
```

**Key Principle**: Each pillar is **completely independent**. You can:
- Test config without touching CLI or guardrails
- Test guardrails without touching config or CLI
- Test CLI without touching either

This independence is critical for unit testing and debugging.

---

## Pillar 1: Base Operation Definition (Core Abstraction)

### BaseOperationDef (Abstract Base Class)

All operations inherit from BaseOperationDef. This is the contract every operation must fulfill.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, TypedDict

class ValidationResult(TypedDict):
    """Validation response structure"""
    valid: bool
    reason: str | None

class BaseOperationDef(ABC):
    """Abstract base for all operations"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Operation name (immutable).
        Example: "get_shop", "list_listings", "create_listing"
        """
        pass
    
    @property
    @abstractmethod
    def operation_type(self) -> str:
        """
        Operation type: READ, WRITE, BULK, or ORCHESTRATED.
        READ: Safe (idempotent, no state change)
        WRITE: Unsafe (requires approval gate)
        BULK: Multiple reads in one call (rate limit: 1 per 5 min)
        ORCHESTRATED: Complex multi-step (rate limit: 1 per 5 min)
        """
        pass
    
    @property
    @abstractmethod
    def rate_limit(self) -> int:
        """
        Rate limit per minute.
        READ: 50/min
        WRITE: 5/min
        BULK: 1 per 5 min
        ORCHESTRATED: 1 per 5 min
        """
        pass
    
    @property
    @abstractmethod
    def requires_approval(self) -> bool:
        """
        Does this operation require approval?
        True: WRITE operations (create, update, delete, approve)
        False: READ operations (get, list)
        """
        pass
    
    @abstractmethod
    def validate(self, arguments: Dict[str, Any]) -> ValidationResult:
        """
        Validate operation arguments BEFORE execution.
        
        Returns:
            {"valid": True, "reason": None} — Arguments OK
            {"valid": False, "reason": "error message"} — Validation failed
        
        Called by CLI before routing to execute().
        """
        pass
    
    @abstractmethod
    def execute(self, arguments: Dict[str, Any], approval_gate=None) -> Dict[str, Any]:
        """
        Execute the operation.
        
        Args:
            arguments: Validated arguments from CLI
            approval_gate: ApprovalGate instance (for WRITE operations)
        
        Returns:
            {
                "status": "COMPLETED" | "FAILED" | "EXECUTING",
                "operation_name": self.name,
                "request_id": "uuid",
                "timestamp": "ISO-8601",
                "data": {...},  # Operation-specific result
                "error": None,  # Error message if failed
                "approval_gate_id": "gate-id"  # For WRITE ops
            }
        
        For WRITE operations, MUST verify:
            1. approval_gate is not None
            2. approval_gate.status == "APPROVED"
            3. not approval_gate.is_expired()
            
        If any check fails, return {"status": "FAILED", "error": "..."}
        """
        pass
    
    @abstractmethod
    def get_tool_schema(self) -> Dict[str, Any]:
        """
        MCP tool schema for this operation.
        
        Returns:
            {
                "name": self.name,
                "description": "What this operation does",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"},
                        "param2": {"type": "integer"}
                    },
                    "required": ["param1"]
                }
            }
        """
        pass
```

### WriteOperationDef (Specialized Subclass for WRITE Operations)

For operations that modify state (create, update, delete, approve):

```python
class WriteOperationDef(BaseOperationDef):
    """
    Base class for write operations.
    
    Enforces approval gate pattern:
    1. Developer creates gate
    2. User reviews and approves/rejects
    3. execute() verifies gate is APPROVED and not expired
    """
    
    @property
    def requires_approval(self) -> bool:
        """Always True for write operations"""
        return True
    
    @abstractmethod
    def execute(self, arguments: Dict[str, Any], approval_gate=None) -> Dict[str, Any]:
        """
        Must verify approval gate before executing.
        
        Pattern:
            if approval_gate is None:
                return {"status": "FAILED", "error": "Approval gate required"}
            if approval_gate.status != "APPROVED":
                return {"status": "FAILED", "error": "Not approved"}
            if approval_gate.is_expired():
                return {"status": "FAILED", "error": "Approval expired"}
            
            # Now execute the operation
            ...
        """
        pass
```

---

## Pillar 2: Operation Registry (Thread-Safe Central Registry)

All operations are registered in a thread-safe central registry that multiple developers can access concurrently.

### OperationRegistry (Thread-Safe Registry)

```python
from threading import RLock
from typing import Dict, List

class OperationRegistry:
    """
    Thread-safe central registry for all operations.
    
    10+ developers register operations concurrently without conflicts.
    Uses RLock (reentrant lock) for thread safety.
    """
    
    def __init__(self):
        self._operations: Dict[str, BaseOperationDef] = {}
        self._lock = RLock()
    
    def register(self, operation: BaseOperationDef) -> None:
        """
        Register a new operation.
        
        Thread-safe: Acquires lock before modifying registry.
        
        Args:
            operation: BaseOperationDef instance
        
        Raises:
            ValueError: If operation with same name already registered
        """
        with self._lock:
            if operation.name in self._operations:
                raise ValueError(f"Operation {operation.name} already registered")
            self._operations[operation.name] = operation
    
    def get(self, name: str) -> BaseOperationDef | None:
        """
        Get operation by name.
        
        Args:
            name: Operation name (e.g., "get_shop")
        
        Returns:
            BaseOperationDef instance or None
        """
        with self._lock:
            return self._operations.get(name)
    
    def list_all(self) -> List[BaseOperationDef]:
        """
        Get all registered operations.
        
        Returns:
            List of all BaseOperationDef instances
        """
        with self._lock:
            return list(self._operations.values())
    
    def list_by_type(self, operation_type: str) -> List[BaseOperationDef]:
        """
        Get operations filtered by type.
        
        Args:
            operation_type: "READ", "WRITE", "BULK", or "ORCHESTRATED"
        
        Returns:
            List of matching operations
        """
        with self._lock:
            return [
                op for op in self._operations.values()
                if op.operation_type == operation_type
            ]
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get MCP tool schemas for all operations.
        
        Used by CLI to expose tools to Claude.
        
        Returns:
            List of tool schema dicts
        """
        with self._lock:
            return [op.get_tool_schema() for op in self._operations.values()]

# Global registry instance
REGISTRY = OperationRegistry()
```

### Registration Pattern

```python
# In src/operations/__init__.py or in each operation module

from src.registry import REGISTRY
from src.operations.my_operation import MyOperation

# Register operation
REGISTRY.register(MyOperation())

# In CLI, operations are accessible globally
op = REGISTRY.get("my_operation")
if op:
    response = op.execute(arguments)
```

---

## Pillar 3: Configuration (4-Level Hierarchy)

Configuration uses a strict 4-level hierarchy. Each level overrides the previous.

### Configuration Hierarchy (Priority Order)

```
1. Environment Variables (HIGHEST PRIORITY)
   ETSY_MCP_API_KEY="from-env"
   
2. Repo Config (~/.claude/etsy-mcp.json)
   {"api_key": "from-repo", "rate_limit": 50}
   
3. Master Config (~/.claude/etsy-mcp.json)
   {"api_key": "from-home", "rate_limit": 40}
   
4. Code Defaults (LOWEST PRIORITY)
   DEFAULTS = {"api_key": None, "rate_limit": 50}
```

### Config Class (Thread-Safe with Caching)

```python
from threading import RLock
from functools import lru_cache
import json
import os

class Config:
    """
    Thread-safe configuration with 4-level hierarchy.
    
    Access pattern: Config.get(key, default)
    Hierarchy is handled automatically.
    """
    
    # Code defaults (lowest priority)
    DEFAULTS = {
        "api_key": None,
        "api_secret": None,
        "rate_limit": 50,
        "approval_ttl_hours": 1,
        "log_level": "INFO",
        "tls_version": "1.3",
        # ... other defaults
    }
    
    _lock = RLock()
    _cache = {}
    
    @classmethod
    def get(cls, key: str, default=None) -> Any:
        """
        Get config value from 4-level hierarchy.
        
        Returns highest priority value available.
        Cached for performance.
        
        Args:
            key: Configuration key
            default: Default if not found anywhere
        
        Returns:
            Configuration value from hierarchy
        """
        with cls._lock:
            # Check cache first
            if key in cls._cache:
                return cls._cache[key]
            
            # Level 1: Environment variables (highest priority)
            env_key = f"ETSY_MCP_{key.upper()}"
            if env_key in os.environ:
                value = os.environ[env_key]
                cls._cache[key] = value
                return value
            
            # Level 2: Repo config
            repo_config = cls._load_json_file(".claude/etsy-mcp.json")
            if repo_config and key in repo_config:
                value = repo_config[key]
                cls._cache[key] = value
                return value
            
            # Level 3: Master config
            master_config = cls._load_json_file(os.path.expanduser("~/.claude/etsy-mcp.json"))
            if master_config and key in master_config:
                value = master_config[key]
                cls._cache[key] = value
                return value
            
            # Level 4: Code defaults (lowest priority)
            if key in cls.DEFAULTS:
                value = cls.DEFAULTS[key]
                cls._cache[key] = value
                return value
            
            # Not found anywhere
            cls._cache[key] = default
            return default
    
    @classmethod
    def _load_json_file(cls, path: str) -> Dict[str, Any] | None:
        """
        Load JSON config file safely.
        
        Returns None if file doesn't exist or is invalid.
        """
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return None
```

### Usage Examples

```python
# Get config values (hierarchy is automatic)
api_key = Config.get("api_key")  # From env, repo, home, or default
rate_limit = Config.get("rate_limit", 50)  # With fallback
tls_version = Config.get("tls_version")  # From hierarchy

# Never do this:
api_key = os.environ.get("ETSY_MCP_API_KEY")  # WRONG: skips hierarchy
api_key = "hardcoded_key"  # WRONG: security violation
```

---

## Operation Models (Data Structures)

### Operation Status Enum

```python
from enum import Enum

class OperationStatus(Enum):
    """Status of an operation throughout its lifecycle"""
    PENDING = "pending"          # Waiting to execute
    APPROVED = "approved"        # Approved by user
    EXECUTING = "executing"      # Currently executing
    COMPLETED = "completed"      # Successfully executed
    FAILED = "failed"            # Execution failed
    CANCELLED = "cancelled"      # Cancelled by user
    EXPIRED = "expired"          # TTL expired
```

### Approval Status Enum

```python
class ApprovalStatus(Enum):
    """Status of an approval gate"""
    PENDING = "pending"          # Waiting for user decision
    APPROVED = "approved"        # User approved
    REJECTED = "rejected"        # User rejected
    EXPIRED = "expired"          # TTL expired without decision
```

### ApprovalGate Class

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

@dataclass
class ApprovalGate:
    """
    Approval gate for WRITE operations.
    
    Workflow:
    1. Create gate: gate = ApprovalGate()
    2. User reviews: print(gate)
    3. User approves: gate.approve()
    4. Execute verifies: gate.status == "APPROVED" and not gate.is_expired()
    
    TTL: 1 hour (configurable)
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    ttl_hours: int = 1
    rejection_reason: str | None = None
    
    def approve(self) -> None:
        """User approves this gate"""
        self.status = ApprovalStatus.APPROVED
    
    def reject(self, reason: str = "User rejected") -> None:
        """User rejects this gate"""
        self.status = ApprovalStatus.REJECTED
        self.rejection_reason = reason
    
    def is_expired(self) -> bool:
        """Check if gate has expired"""
        expiry_time = self.created_at + timedelta(hours=self.ttl_hours)
        return datetime.utcnow() > expiry_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging/display"""
        return {
            "id": self.id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "ttl_hours": self.ttl_hours,
            "is_expired": self.is_expired(),
            "rejection_reason": self.rejection_reason
        }
```

### OperationRequest Dataclass

```python
from dataclasses import dataclass, field

@dataclass
class OperationRequest:
    """
    Complete operation request with full lifecycle tracking.
    
    Represents a single operation from submission to completion.
    """
    
    operation_name: str
    arguments: Dict[str, Any]
    operation_type: str  # READ, WRITE, BULK, ORCHESTRATED
    ttl_hours: int = 1
    
    # Auto-populated
    created_at: datetime = field(default_factory=datetime.utcnow)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OperationStatus = OperationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    approval_gate_id: str | None = None
    
    # Execution results
    result: Dict[str, Any] | None = None
    error: str | None = None
```

---

## Guardrails (Safety and Rate Limiting)

### Rate Limiting

```python
from collections import defaultdict
from time import time

class RateLimiter:
    """
    Token bucket rate limiter.
    
    Limits operations per minute based on operation type.
    """
    
    LIMITS = {
        "READ": 50,           # 50 per minute
        "WRITE": 5,           # 5 per minute
        "BULK": 1,            # 1 per 5 minutes (token fills every 5 min)
        "ORCHESTRATED": 1     # 1 per 5 minutes
    }
    
    def __init__(self):
        self._tokens = defaultdict(lambda: self.LIMITS.get("READ", 50))
        self._last_refill = defaultdict(time)
    
    def is_allowed(self, operation_type: str) -> bool:
        """
        Check if operation is allowed under rate limit.
        
        Returns:
            True: Operation allowed
            False: Rate limit exceeded
        """
        limit = self.LIMITS.get(operation_type, 50)
        current_time = time()
        
        # Refill tokens based on time passed
        if operation_type in self._last_refill:
            time_passed = current_time - self._last_refill[operation_type]
            # For 5-minute operations: refill if 5 minutes passed
            refill_interval = 300 if operation_type in ["BULK", "ORCHESTRATED"] else 60
            if time_passed >= refill_interval:
                self._tokens[operation_type] = limit
                self._last_refill[operation_type] = current_time
        else:
            self._last_refill[operation_type] = current_time
        
        if self._tokens[operation_type] > 0:
            self._tokens[operation_type] -= 1
            return True
        
        return False
```

---

## Thread-Safety Patterns

### Pattern 1: Use Config.get() Not os.environ

```python
# ✓ CORRECT
api_key = Config.get("api_key")
rate_limit = Config.get("rate_limit")

# ✗ WRONG
api_key = os.environ.get("ETSY_MCP_API_KEY")
```

### Pattern 2: Use REGISTRY Not Direct Instantiation

```python
# ✓ CORRECT
from src.registry import REGISTRY
op = REGISTRY.get("my_operation")

# ✗ WRONG
from src.operations.my_operation import MyOperation
op = MyOperation()  # Creates new instance, bypasses registry
```

### Pattern 3: MockEtsyAPI Has Fixed Immutable Fixtures

```python
# ✓ CORRECT - These never change
LISTING_IDS = [101, 102, 103]
ORDER_IDS = [201, 202]

# ✗ WRONG - Don't modify
mock_api.LISTING_IDS.append(104)
```

### Pattern 4: Test Isolation By PID

```python
# ✓ CORRECT - Each test gets its own database
import os
db_path = f"tests/fixtures/test_{os.getpid()}.db"

# ✗ WRONG - Tests interfere with each other
db_path = "tests/fixtures/test.db"
```

---

## Operation Response Format

All operations return this standard response structure:

```python
{
    "status": str,                    # COMPLETED, FAILED, EXECUTING, etc.
    "operation_name": str,            # From operation.name
    "request_id": str,                # UUID for tracing
    "timestamp": str,                 # ISO-8601 UTC
    
    # Success case
    "data": {
        # Operation-specific result
        "shop_id": 123,
        "listings": [...],
        # etc.
    },
    
    # Failure case
    "error": str | None,              # Error message if failed
    
    # For WRITE operations
    "approval_gate_id": str | None    # Gate that was used
}
```

### Example Responses

**READ Operation (Success):**
```python
{
    "status": "COMPLETED",
    "operation_name": "list_listings",
    "request_id": "uuid-123",
    "timestamp": "2026-05-29T10:30:00Z",
    "data": {
        "listings": [
            {"listing_id": 101, "title": "Horror Mask"},
            {"listing_id": 102, "title": "Skeleton Costume"}
        ],
        "count": 2
    },
    "error": None
}
```

**WRITE Operation (Approval Required):**
```python
{
    "status": "FAILED",
    "operation_name": "create_listing",
    "request_id": "uuid-456",
    "timestamp": "2026-05-29T10:30:00Z",
    "data": None,
    "error": "Approval gate required",
    "approval_gate_id": "gate-789"
}
```

**WRITE Operation (Approved and Executed):**
```python
{
    "status": "COMPLETED",
    "operation_name": "create_listing",
    "request_id": "uuid-456",
    "timestamp": "2026-05-29T10:30:00Z",
    "data": {
        "listing_id": 103,
        "title": "New Horror Mask",
        "state": "active"
    },
    "error": None,
    "approval_gate_id": "gate-789"
}
```

---

## Testing Architecture

### Test Organization

```
tests/
├── fixtures/
│   └── mock_etsy_api.py          # MockEtsyAPI with FIXED data
├── test_fixtures.py              # Tests for mock API
├── test_config.py                # Tests for Config hierarchy
├── test_registry.py              # Tests for OperationRegistry
├── test_operation_models.py      # Tests for ApprovalGate, etc.
├── test_p1_read_a.py             # Tests for P1 Read-A operations
├── test_p1_read_b.py             # Tests for P1 Read-B operations
├── test_p2_write_a.py            # Tests for P2 Write-A operations
├── test_p2_write_b.py            # Tests for P2 Write-B operations
├── test_p2_write_c.py            # Tests for P2 Write-C operations
├── test_infrastructure.py         # Tests for orchestration
└── integration/
    └── test_workflows.py         # End-to-end integration tests
```

### Test Fixtures Pattern

```python
import pytest
from src.operations.my_operation import MyOperation
from src.operation_models import ApprovalGate

@pytest.fixture
def operation():
    """Each test gets a fresh operation instance"""
    return MyOperation()

@pytest.fixture
def approved_gate():
    """Pre-approved gate for testing execution"""
    gate = ApprovalGate()
    gate.approve()
    return gate

class TestMyOperation:
    def test_properties(self, operation):
        assert operation.name == "my_operation"
        assert operation.operation_type == "READ"
        assert operation.rate_limit == 50
    
    def test_validation_success(self, operation):
        result = operation.validate({"valid_arg": "value"})
        assert result["valid"] is True
    
    def test_validation_failure(self, operation):
        result = operation.validate({})
        assert result["valid"] is False
    
    def test_execution(self, operation):
        response = operation.execute({"valid_arg": "value"})
        assert response["status"] == "COMPLETED"
    
    def test_schema(self, operation):
        schema = operation.get_tool_schema()
        assert "name" in schema
        assert "inputSchema" in schema
```

---

## Summary

This architecture ensures:

1. **Independence**: Each pillar testable in isolation
2. **Concurrency**: 10+ developers work simultaneously
3. **Type Safety**: Full type hints, mypy --strict compliance
4. **Security**: No hardcoded secrets, approval gates, TLS enforcement
5. **Reliability**: Thread-safe operations, immutable fixtures
6. **Maintainability**: Clear separation of concerns, documented patterns
7. **Scalability**: Registry pattern allows unlimited operations

All operations follow this same pattern, ensuring consistency across the codebase.
