"""Central registry of all operations (P1-P4, DRY pattern)."""

from typing import Any

from src.operations import BaseOperationDef, Operation


class OperationRegistry:
    """Registry of all available operations (P1-P4)."""

    def __init__(self):
        self._operations: dict[str, BaseOperationDef] = {}

    def register(self, op_def: BaseOperationDef) -> None:
        """Register an operation definition."""
        if not op_def.name:
            raise ValueError("Operation definition must have a name")
        if op_def.name in self._operations:
            raise ValueError(f"Operation '{op_def.name}' is already registered")
        self._operations[op_def.name] = op_def

    def get(self, name: str) -> BaseOperationDef | None:
        """Get operation definition by name."""
        return self._operations.get(name)

    def list_all(self) -> list[BaseOperationDef]:
        """Get all registered operations."""
        return list(self._operations.values())

    def list_by_type(self, operation_type: Operation) -> list[BaseOperationDef]:
        """Get operations by type."""
        return [op for op in self._operations.values() if op.operation_type == operation_type]

    def list_read_only(self) -> list[BaseOperationDef]:
        """Get all read-only operations (P1)."""
        return self.list_by_type(Operation.READ)

    def list_write(self) -> list[BaseOperationDef]:
        """Get all write operations (P2)."""
        return self.list_by_type(Operation.WRITE)

    def list_bulk(self) -> list[BaseOperationDef]:
        """Get all bulk operations (P3)."""
        return self.list_by_type(Operation.BULK)

    def list_orchestrated(self) -> list[BaseOperationDef]:
        """Get all orchestrated operations (P4)."""
        return self.list_by_type(Operation.ORCHESTRATED)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Generate all MCP tool schemas (used by server.list_tools())."""
        return [op.get_tool_schema() for op in self._operations.values()]

    def validate_operation(self, name: str, arguments: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate operation exists and arguments are correct.

        Returns: (is_valid, errors)
        """
        op_def = self.get(name)
        if not op_def:
            return False, [f"Unknown operation: {name}"]

        errors = op_def.validate(arguments)
        return len(errors) == 0, errors


# Global registry instance
REGISTRY = OperationRegistry()
