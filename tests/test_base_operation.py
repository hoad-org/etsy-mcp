"""Tests for BaseOperationDef and WriteOperationDef abstract classes."""

import pytest

from src.base_operation import BaseOperationDef, Operation, ValidationResult, WriteOperationDef


class ConcreteReadOperation(BaseOperationDef):
    """Concrete READ operation for testing."""

    @property
    def name(self) -> str:
        return "test_read_op"

    @property
    def operation_type(self) -> Operation:
        return Operation.READ

    @property
    def rate_limit(self) -> int:
        return 50

    @property
    def requires_approval(self) -> bool:
        return False

    def validate(self, arguments):
        if not arguments:
            return ValidationResult(valid=True, reason=None)
        if "required_field" not in arguments:
            return ValidationResult(valid=False, reason="missing required_field")
        return ValidationResult(valid=True, reason=None)

    def execute(self, arguments):
        return {"status": "completed", "data": "test"}

    def get_tool_schema(self):
        return {
            "name": self.name,
            "description": "Test read operation",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }


class ConcreteWriteOperation(WriteOperationDef):
    """Concrete WRITE operation for testing."""

    @property
    def name(self) -> str:
        return "test_write_op"

    @property
    def operation_type(self) -> Operation:
        return Operation.WRITE

    @property
    def rate_limit(self) -> int:
        return 5

    def validate(self, arguments):
        if "title" not in arguments or not arguments["title"]:
            return ValidationResult(valid=False, reason="title required")
        return ValidationResult(valid=True, reason=None)

    def execute(self, arguments, approval_gate=None):
        if approval_gate and approval_gate.get("status") != "APPROVED":
            return {"status": "failed", "error": "approval required"}
        return {"status": "completed", "approval_gate_id": approval_gate.get("id") if approval_gate else None}

    def get_tool_schema(self):
        return {
            "name": self.name,
            "description": "Test write operation",
            "inputSchema": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
                "required": ["title"],
                "additionalProperties": False
            }
        }


class TestOperation:
    """Test Operation enum."""

    def test_operation_values(self):
        """Test Operation enum values."""
        assert Operation.READ.value == "read"
        assert Operation.WRITE.value == "write"
        assert Operation.BULK.value == "bulk"
        assert Operation.ORCHESTRATED.value == "orchestrated"

    def test_operation_comparison(self):
        """Test Operation enum comparison."""
        assert Operation.READ == Operation.READ
        assert Operation.READ != Operation.WRITE


class TestValidationResult:
    """Test ValidationResult TypedDict."""

    def test_validation_result_valid(self):
        """Test valid ValidationResult."""
        result = ValidationResult(valid=True, reason=None)
        assert result["valid"] is True
        assert result["reason"] is None

    def test_validation_result_invalid(self):
        """Test invalid ValidationResult."""
        result = ValidationResult(valid=False, reason="test error")
        assert result["valid"] is False
        assert result["reason"] == "test error"


class TestBaseOperationDef:
    """Test BaseOperationDef abstract class."""

    def test_abstract_cannot_instantiate(self):
        """Test that BaseOperationDef cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseOperationDef()

    def test_concrete_read_operation_properties(self):
        """Test concrete READ operation properties."""
        op = ConcreteReadOperation()
        assert op.name == "test_read_op"
        assert op.operation_type == Operation.READ
        assert op.rate_limit == 50
        assert op.requires_approval is False

    def test_concrete_read_operation_repr(self):
        """Test __repr__ method."""
        op = ConcreteReadOperation()
        assert "ConcreteReadOperation" in repr(op)
        assert "test_read_op" in repr(op)
        assert "read" in repr(op)

    def test_validate_success(self):
        """Test successful validation."""
        op = ConcreteReadOperation()
        result = op.validate({})
        assert result["valid"] is True
        assert result["reason"] is None

    def test_validate_failure(self):
        """Test validation failure."""
        op = ConcreteReadOperation()
        result = op.validate({"invalid_field": "value"})
        assert result["valid"] is False
        assert result["reason"] == "missing required_field"

    def test_execute(self):
        """Test execute method."""
        op = ConcreteReadOperation()
        result = op.execute({})
        assert result["status"] == "completed"
        assert result["data"] == "test"

    def test_get_tool_schema(self):
        """Test get_tool_schema method."""
        op = ConcreteReadOperation()
        schema = op.get_tool_schema()
        assert schema["name"] == "test_read_op"
        assert schema["description"] == "Test read operation"
        assert "inputSchema" in schema
        assert schema["inputSchema"]["type"] == "object"


class TestWriteOperationDef:
    """Test WriteOperationDef class."""

    def test_requires_approval_always_true(self):
        """Test that WriteOperationDef always requires approval."""
        op = ConcreteWriteOperation()
        assert op.requires_approval is True

    def test_concrete_write_operation_properties(self):
        """Test concrete WRITE operation properties."""
        op = ConcreteWriteOperation()
        assert op.name == "test_write_op"
        assert op.operation_type == Operation.WRITE
        assert op.rate_limit == 5
        assert op.requires_approval is True

    def test_validate_write_success(self):
        """Test successful WRITE operation validation."""
        op = ConcreteWriteOperation()
        result = op.validate({"title": "New Product"})
        assert result["valid"] is True
        assert result["reason"] is None

    def test_validate_write_failure(self):
        """Test WRITE operation validation failure."""
        op = ConcreteWriteOperation()
        result = op.validate({"title": ""})
        assert result["valid"] is False
        assert result["reason"] == "title required"

    def test_execute_write_without_approval(self):
        """Test execute without approval gate."""
        op = ConcreteWriteOperation()
        result = op.execute({"title": "Product"})
        assert result["status"] == "completed"

    def test_execute_write_with_approval(self):
        """Test execute with approval gate."""
        op = ConcreteWriteOperation()
        gate = {"id": "gate-123", "status": "APPROVED"}
        result = op.execute({"title": "Product"}, approval_gate=gate)
        assert result["status"] == "completed"
        assert result["approval_gate_id"] == "gate-123"

    def test_execute_write_with_unapproved_gate(self):
        """Test execute with unapproved gate."""
        op = ConcreteWriteOperation()
        gate = {"id": "gate-123", "status": "PENDING"}
        result = op.execute({"title": "Product"}, approval_gate=gate)
        assert result["status"] == "failed"
        assert "approval required" in result["error"]

    def test_get_tool_schema_write(self):
        """Test WRITE operation tool schema."""
        op = ConcreteWriteOperation()
        schema = op.get_tool_schema()
        assert schema["name"] == "test_write_op"
        assert "title" in schema["inputSchema"]["properties"]
        assert "title" in schema["inputSchema"]["required"]
