"""Operation abstractions for P1-P4 phases (DRY pattern)."""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any


class Operation(Enum):
    """Operation type enumeration (phase designation)."""

    READ = "read"  # P1: immediate, no gates
    WRITE = "write"  # P2: requires approval
    BULK = "bulk"  # P3: batched async
    ORCHESTRATED = "orchestrated"  # P4: Step Functions


class OperationStatus(Enum):
    """Lifecycle state of an operation."""

    PENDING = "pending"  # Queued, waiting for execution
    APPROVED = "approved"  # Gate passed, ready to execute
    EXECUTING = "executing"  # In progress
    COMPLETED = "completed"  # Success
    FAILED = "failed"  # Error
    CANCELLED = "cancelled"  # User cancelled
    EXPIRED = "expired"  # TTL exceeded


class ApprovalStatus(Enum):
    """Lifecycle state of an approval gate."""

    PENDING = "pending"  # Awaiting approval
    APPROVED = "approved"  # Approved
    REJECTED = "rejected"  # Rejected by approver
    EXPIRED = "expired"  # TTL exceeded


class ParameterSchema:
    """Parameter specification for validation."""

    def __init__(
        self,
        param_type: str,  # "string", "integer", "array", etc.
        description: str = "",
        default: Any = None,
        required: bool = False,
        enum_values: list[str] | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
    ):
        self.param_type = param_type
        self.description = description
        self.default = default
        self.required = required
        self.enum_values = enum_values
        self.min_value = min_value
        self.max_value = max_value

    def to_schema(self) -> dict[str, Any]:
        """Convert to JSON schema format."""
        schema: dict[str, Any] = {"type": self.param_type, "description": self.description}
        if self.enum_values:
            schema["enum"] = self.enum_values
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        if self.default is not None:
            schema["default"] = self.default
        return schema


class BaseOperationDef(ABC):
    """Base class for all operation definitions (DRY pattern)."""

    # Subclasses must override these
    name: str = ""
    operation_type: Operation = Operation.READ
    description: str = ""
    rate_limit_type: str = "read"  # "read", "write", "dangerous"
    parameters: dict[str, ParameterSchema] = {}
    required_params: list[str] = []

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        """Validate arguments. Return list of errors (empty if valid)."""
        errors = []

        # Check required parameters
        for param_name in self.required_params:
            if param_name not in arguments:
                errors.append(f"Required parameter '{param_name}' is missing")

        # Validate parameter types and constraints
        for param_name, param_value in arguments.items():
            if param_name not in self.parameters:
                errors.append(f"Unknown parameter '{param_name}'")
                continue

            param_spec = self.parameters[param_name]

            # Type validation
            type_mapping = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict,
            }
            expected_type = type_mapping.get(param_spec.param_type)
            if expected_type and not isinstance(param_value, expected_type):
                errors.append(
                    f"Parameter '{param_name}' must be of type {param_spec.param_type}, "
                    f"got {type(param_value).__name__}"
                )
                continue

            # Enum validation
            if param_spec.enum_values and param_value not in param_spec.enum_values:
                errors.append(
                    f"Parameter '{param_name}' must be one of {param_spec.enum_values}, "
                    f"got {param_value}"
                )

            # Range validation (for integers/numbers)
            if isinstance(param_value, (int, float)):
                if param_spec.min_value is not None and param_value < param_spec.min_value:
                    errors.append(
                        f"Parameter '{param_name}' must be >= {param_spec.min_value}, "
                        f"got {param_value}"
                    )
                if param_spec.max_value is not None and param_value > param_spec.max_value:
                    errors.append(
                        f"Parameter '{param_name}' must be <= {param_spec.max_value}, "
                        f"got {param_value}"
                    )

        return errors

    @abstractmethod
    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        """Execute operation. Must be implemented by subclass."""
        raise NotImplementedError(f"execute() not implemented for {self.name}")

    def get_tool_schema(self) -> dict[str, Any]:
        """Generate MCP tool schema for registration."""
        properties = {}
        for param_name, param_spec in self.parameters.items():
            properties[param_name] = param_spec.to_schema()

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": self.required_params,
            },
        }


class ApprovalGate:
    """Authorization gate for write operations (P2)."""

    def __init__(
        self,
        operation_id: str,
        requested_by: str,
        ttl_minutes: int = 60,
    ):
        self.id: str = uuid.uuid4().hex
        self.operation_id = operation_id
        self.requested_by = requested_by
        self.created_at = datetime.now(UTC)
        self.expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        self.status = ApprovalStatus.PENDING
        self.approver: str | None = None
        self.approval_timestamp: datetime | None = None
        self.reason: str | None = None

    def is_expired(self) -> bool:
        """Check if gate has expired."""
        return datetime.now(UTC) > self.expires_at

    def approve(self, approver: str, reason: str | None = None) -> None:
        """Approve the gate."""
        self.status = ApprovalStatus.APPROVED
        self.approver = approver
        self.approval_timestamp = datetime.now(UTC)
        self.reason = reason

    def reject(self, approver: str, reason: str) -> None:
        """Reject the gate."""
        self.status = ApprovalStatus.REJECTED
        self.approver = approver
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "operation_id": self.operation_id,
            "requested_by": self.requested_by,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "approver": self.approver,
            "approval_timestamp": self.approval_timestamp.isoformat() if self.approval_timestamp else None,
            "reason": self.reason,
        }


class OperationRequest:
    """Request to execute an operation (P1-P4 unified model)."""

    def __init__(
        self,
        operation_name: str,
        arguments: dict[str, Any],
        operation_type: Operation,
        ttl_hours: int = 24,
    ):
        self.id: str = uuid.uuid4().hex
        self.operation_name = operation_name
        self.arguments = arguments
        self.operation_type = operation_type
        self.status = OperationStatus.PENDING
        self.created_at = datetime.now(UTC)
        self.executed_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        self.ttl = timedelta(hours=ttl_hours)

        # For P2 (gates)
        self.approval_gate: ApprovalGate | None = None
        self.approved_by: str | None = None
        self.approval_reason: str | None = None

        # For P3 (bulk)
        self.is_bulk = False
        self.bulk_parent_id: str | None = None
        self.bulk_sub_operation_ids: list[str] = []

        # For P4 (orchestration)
        self.step_function_arn: str | None = None
        self.step_function_execution_id: str | None = None

        # Results
        self.result: Any | None = None
        self.error: str | None = None

        # Metadata (for retry logic, etc.)
        self._metadata: dict[str, Any] = {}

    def is_expired(self) -> bool:
        """Check if operation has expired (TTL exceeded)."""
        return datetime.now(UTC) > self.expires_at

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self._metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self._metadata[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "operation_name": self.operation_name,
            "arguments": self.arguments,
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat(),
            "approval_gate": self.approval_gate.to_dict() if self.approval_gate else None,
            "result": self.result,
            "error": self.error,
            "is_bulk": self.is_bulk,
            "bulk_parent_id": self.bulk_parent_id,
            "bulk_sub_operation_ids": self.bulk_sub_operation_ids,
            "step_function_arn": self.step_function_arn,
            "step_function_execution_id": self.step_function_execution_id,
        }

    def to_audit_log(self, redact_keys: list[str] | None = None) -> dict[str, Any]:
        """Convert to audit log entry (for redaction and logging)."""
        redact_keys = redact_keys or []
        return {
            "operation_id": self.id,
            "operation_name": self.operation_name,
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "approval_gate_id": self.approval_gate.id if self.approval_gate else None,
            "approved_by": self.approved_by,
            "error": self.error,
        }
