"""
BaseOperationDef and WriteOperationDef abstract base classes.

All 18 operations (6 P1 read, 5 P2 write, 4 P3 bulk, 3+ P4 orchestrated) inherit from these.
This module defines the rigid contract ensuring all developers implement identically.

Thread-safety: Classes are stateless; no shared mutable state.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, TypedDict


class Operation(Enum):
    """Operation type categories with rate limits."""
    READ = "read"                  # 50/min
    WRITE = "write"                # 5/min
    BULK = "bulk"                  # 1/5min
    ORCHESTRATED = "orchestrated"  # 1/5min


class ValidationResult(TypedDict):
    """Result of operation argument validation."""
    valid: bool
    reason: Optional[str]  # None if valid, error message if invalid


class BaseOperationDef(ABC):
    """Abstract base class for all MCP operations.

    Every operation (P1-P4) must subclass this and implement:
    - validate(arguments: dict) -> ValidationResult
    - execute(arguments: dict) -> dict
    - get_tool_schema() -> dict

    Properties define rate limiting and approval requirements.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique operation name (e.g., 'get_shop_info').

        Used as key in REGISTRY[Operation.READ].register(name, self)
        """
        pass

    @property
    @abstractmethod
    def operation_type(self) -> Operation:
        """Operation category (READ, WRITE, BULK, ORCHESTRATED)."""
        pass

    @property
    @abstractmethod
    def rate_limit(self) -> int:
        """Requests per minute (50 for READ, 5 for WRITE, etc.)."""
        pass

    @property
    @abstractmethod
    def requires_approval(self) -> bool:
        """True if operation needs ApprovalGate (all WRITE ops do; some READ/BULK).

        Approval workflow:
        1. Operation created with status=PENDING
        2. ApprovalGate created (1-hour TTL)
        3. User shares approval_gate_id with approver
        4. Approver calls approve_operation(gate_id) -> status=APPROVED
        5. OperationQueue picks up APPROVED operation
        6. execute() called -> Etsy API -> status=COMPLETED
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, type={self.operation_type.value})"

    @abstractmethod
    def validate(self, arguments: Dict[str, Any]) -> ValidationResult:
        """Validate operation arguments before execution.

        Args:
            arguments: Dict of operation-specific arguments

        Returns:
            ValidationResult: {valid: bool, reason: error_message if invalid}

        Contract:
        - All required arguments must be present
        - All arguments must match expected types/ranges
        - Custom business logic validation (e.g., title length, price range)
        - Return immediately on first validation failure

        Examples:
            GetShopInfoOperation.validate({}) -> ValidationResult(valid=True, reason=None)
            ListListingsOperation.validate({}) -> ValidationResult(valid=False, reason="page required")
            UpdateListingOperation.validate({"listing_id": "abc", "title": ""})
                -> ValidationResult(valid=False, reason="title cannot be empty")
        """
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation against Etsy API (or mock).

        Args:
            arguments: Dict validated by validate()

        Returns:
            Dict with operation-specific response. Always includes:
            - status: "completed" | "failed"
            - Any other response fields from Etsy API or mock

        Contract:
        - Called ONLY after validate() returns valid=True
        - Must be idempotent (calling twice with same args = same result)
        - Must NOT modify arguments dict
        - Must NOT log credentials/tokens (redact in logs)
        - Exceptions raised here are caught by OperationQueue (retry logic)

        Examples:
            GetShopInfoOperation.execute({}) -> {
                "status": "completed",
                "shop_id": "12345",
                "shop_name": "MyShop",
                "currency_code": "USD",
                ...
            }
        """
        pass

    @abstractmethod
    def get_tool_schema(self) -> Dict[str, Any]:
        """Return JSON-RPC tool schema for Claude/MCP integration.

        Returns:
            Dict matching JSON-RPC 2.0 schema format:
            {
                "name": self.name,
                "description": "Human-readable description",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "arg_name": {"type": "string", "description": "..."},
                        ...
                    },
                    "required": ["required_args"],
                    "additionalProperties": false
                }
            }

        Contract:
        - All properties in schema must match validate() expectations
        - "required" array lists arguments without defaults
        - Descriptions must be clear for Claude to understand usage

        Examples:
            GetShopInfoOperation.get_tool_schema() -> {
                "name": "get_shop_info",
                "description": "Retrieve authenticated shop information",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": false
                }
            }
        """
        pass


class WriteOperationDef(BaseOperationDef):
    """Specialized BaseOperationDef for write operations.

    Write operations (UPDATE, CREATE, DELETE) must:
    1. Have requires_approval = True
    2. Accept approval_gate in execute() signature
    3. Not execute until ApprovalGate.status = APPROVED

    All 5 P2 operations (update_listing, update_listing_inventory, create_order,
    ship_order, cancel_order) inherit from this.
    """

    @property
    def requires_approval(self) -> bool:
        """All write operations require approval."""
        return True

    @abstractmethod
    def execute(
        self,
        arguments: Dict[str, Any],
        approval_gate: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute write operation with approval gate.

        Args:
            arguments: Dict validated by validate()
            approval_gate: ApprovalGate dict with status=APPROVED

        Returns:
            Dict with operation-specific response, including approval_gate_id

        Contract:
        - Called ONLY if approval_gate.status = APPROVED
        - Called ONLY after ApprovalGate.expires_at > now()
        - Must include approval_gate_id in response for audit trail
        - Must log operation with user/approver/timestamp for compliance
        - Exceptions are caught and retried by OperationQueue (max 3 retries)
        """
        pass
