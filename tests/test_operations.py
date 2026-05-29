"""Tests for Operation, ApprovalGate, and OperationRequest classes."""

from datetime import UTC, datetime, timedelta

from src.operations import (
    ApprovalGate,
    ApprovalStatus,
    Operation,
    OperationRequest,
    OperationStatus,
    ParameterSchema,
)


class TestParameterSchema:
    """Test ParameterSchema class."""

    def test_string_schema(self):
        """Test string parameter schema."""
        schema = ParameterSchema("string", description="Name field")
        result = schema.to_schema()
        assert result["type"] == "string"
        assert result["description"] == "Name field"

    def test_integer_schema_with_bounds(self):
        """Test integer parameter with min/max."""
        schema = ParameterSchema(
            "integer",
            description="Count",
            min_value=1,
            max_value=100,
        )
        result = schema.to_schema()
        assert result["type"] == "integer"
        assert result["minimum"] == 1
        assert result["maximum"] == 100

    def test_enum_schema(self):
        """Test enum parameter schema."""
        schema = ParameterSchema(
            "string",
            enum_values=["active", "inactive"],
        )
        result = schema.to_schema()
        assert result["enum"] == ["active", "inactive"]

    def test_schema_with_default(self):
        """Test parameter with default value."""
        schema = ParameterSchema("string", default="test_value")
        result = schema.to_schema()
        assert result["default"] == "test_value"


class TestApprovalGate:
    """Test ApprovalGate class."""

    def test_initialization(self):
        """Test ApprovalGate initialization."""
        gate = ApprovalGate("op_123", "user@example.com")
        assert gate.operation_id == "op_123"
        assert gate.requested_by == "user@example.com"
        assert gate.status == ApprovalStatus.PENDING
        assert gate.id is not None
        assert len(gate.id) == 32  # UUID hex without dashes

    def test_is_expired_false(self):
        """Test is_expired returns False for fresh gate."""
        gate = ApprovalGate("op_123", "user@example.com", ttl_minutes=60)
        assert gate.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired gate."""
        gate = ApprovalGate("op_123", "user@example.com", ttl_minutes=0)
        # Manually set expires_at to past
        gate.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        assert gate.is_expired() is True

    def test_approve(self):
        """Test approve method."""
        gate = ApprovalGate("op_123", "user@example.com")
        gate.approve("approver@example.com", reason="LGTM")
        assert gate.status == ApprovalStatus.APPROVED
        assert gate.approver == "approver@example.com"
        assert gate.reason == "LGTM"
        assert gate.approval_timestamp is not None

    def test_reject(self):
        """Test reject method."""
        gate = ApprovalGate("op_123", "user@example.com")
        gate.reject("approver@example.com", reason="Missing validation")
        assert gate.status == ApprovalStatus.REJECTED
        assert gate.approver == "approver@example.com"
        assert gate.reason == "Missing validation"

    def test_to_dict(self):
        """Test to_dict serialization."""
        gate = ApprovalGate("op_123", "user@example.com")
        gate.approve("approver@example.com")
        result = gate.to_dict()
        assert result["id"] == gate.id
        assert result["operation_id"] == "op_123"
        assert result["requested_by"] == "user@example.com"
        assert result["status"] == "approved"
        assert result["approver"] == "approver@example.com"
        assert result["approval_timestamp"] is not None


class TestOperationRequest:
    """Test OperationRequest class."""

    def test_initialization(self):
        """Test OperationRequest initialization."""
        op = OperationRequest("test_op", {"key": "value"}, Operation.READ)
        assert op.operation_name == "test_op"
        assert op.arguments == {"key": "value"}
        assert op.operation_type == Operation.READ
        assert op.status == OperationStatus.PENDING
        assert op.id is not None

    def test_is_expired_false(self):
        """Test is_expired returns False for fresh operation."""
        op = OperationRequest("test_op", {}, Operation.READ, ttl_hours=24)
        assert op.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired operation."""
        op = OperationRequest("test_op", {}, Operation.READ, ttl_hours=0)
        # Manually set expires_at to past
        op.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        assert op.is_expired() is True

    def test_get_metadata_default(self):
        """Test get_metadata returns default for missing key."""
        op = OperationRequest("test_op", {}, Operation.READ)
        assert op.get_metadata("nonexistent") is None
        assert op.get_metadata("nonexistent", "default") == "default"

    def test_set_metadata(self):
        """Test set_metadata."""
        op = OperationRequest("test_op", {}, Operation.READ)
        op.set_metadata("retry_count", 3)
        assert op.get_metadata("retry_count") == 3

    def test_to_dict(self):
        """Test to_dict serialization."""
        op = OperationRequest("test_op", {"arg": "value"}, Operation.WRITE)
        op.status = OperationStatus.COMPLETED
        op.result = {"status": "success"}
        result = op.to_dict()
        assert result["id"] == op.id
        assert result["operation_name"] == "test_op"
        assert result["operation_type"] == "write"
        assert result["status"] == "completed"
        assert result["arguments"] == {"arg": "value"}
        assert result["result"] == {"status": "success"}

    def test_to_audit_log(self):
        """Test to_audit_log serialization."""
        op = OperationRequest("test_op", {}, Operation.READ)
        op.status = OperationStatus.COMPLETED
        result = op.to_audit_log()
        assert result["operation_id"] == op.id
        assert result["operation_name"] == "test_op"
        assert result["operation_type"] == "read"
        assert result["status"] == "completed"

    def test_with_approval_gate(self):
        """Test OperationRequest with approval gate."""
        op = OperationRequest("test_op", {}, Operation.WRITE)
        gate = ApprovalGate(op.id, "user@example.com")
        op.approval_gate = gate
        result = op.to_dict()
        assert result["approval_gate"] is not None
        assert result["approval_gate"]["id"] == gate.id


class TestOperationEnum:
    """Test Operation enum."""

    def test_all_enum_values(self):
        """Test all Operation enum values."""
        assert Operation.READ.value == "read"
        assert Operation.WRITE.value == "write"
        assert Operation.BULK.value == "bulk"
        assert Operation.ORCHESTRATED.value == "orchestrated"

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert Operation.READ == Operation.READ
        assert Operation.READ != Operation.WRITE


class TestOperationStatus:
    """Test OperationStatus enum."""

    def test_all_status_values(self):
        """Test all OperationStatus enum values."""
        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.APPROVED.value == "approved"
        assert OperationStatus.EXECUTING.value == "executing"
        assert OperationStatus.COMPLETED.value == "completed"
        assert OperationStatus.FAILED.value == "failed"
        assert OperationStatus.CANCELLED.value == "cancelled"
        assert OperationStatus.EXPIRED.value == "expired"


class TestApprovalStatus:
    """Test ApprovalStatus enum."""

    def test_all_approval_status_values(self):
        """Test all ApprovalStatus enum values."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.EXPIRED.value == "expired"


class TestBaseOperationDefValidation:
    """Test BaseOperationDef validation error paths."""

    def test_unknown_parameter_error(self):
        """Test validation catches unknown parameters."""
        from src.operations import BaseOperationDef

        class TestOp(BaseOperationDef):
            name = "test_op"
            operation_type = Operation.READ
            rate_limit = 50
            requires_approval = False
            parameters = {"known_param": ParameterSchema("string")}
            required_params = []

            def validate(self, arguments):
                return super().validate(arguments)

            def execute(self, api, arguments):
                return {}

            def get_tool_schema(self):
                return {}

        op = TestOp()
        errors = op.validate({"unknown_param": "value"})
        assert len(errors) > 0
        assert any("Unknown parameter" in e for e in errors)

    def test_type_validation_error(self):
        """Test validation catches type mismatches."""
        from src.operations import BaseOperationDef

        class TestOp(BaseOperationDef):
            name = "test_op"
            operation_type = Operation.READ
            rate_limit = 50
            requires_approval = False
            parameters = {"count": ParameterSchema("integer")}
            required_params = ["count"]

            def validate(self, arguments):
                return super().validate(arguments)

            def execute(self, api, arguments):
                return {}

            def get_tool_schema(self):
                return {}

        op = TestOp()
        errors = op.validate({"count": "not_an_integer"})
        assert len(errors) > 0
        assert any("must be of type integer" in e for e in errors)

    def test_enum_validation_error(self):
        """Test validation catches enum constraint violations."""
        from src.operations import BaseOperationDef

        class TestOp(BaseOperationDef):
            name = "test_op"
            operation_type = Operation.READ
            rate_limit = 50
            requires_approval = False
            parameters = {
                "status": ParameterSchema(
                    "string",
                    enum_values=["active", "inactive"]
                )
            }
            required_params = ["status"]

            def validate(self, arguments):
                return super().validate(arguments)

            def execute(self, api, arguments):
                return {}

            def get_tool_schema(self):
                return {}

        op = TestOp()
        errors = op.validate({"status": "invalid_value"})
        assert len(errors) > 0
        assert any("must be one of" in e for e in errors)

    def test_min_value_validation_error(self):
        """Test validation catches min value violations."""
        from src.operations import BaseOperationDef

        class TestOp(BaseOperationDef):
            name = "test_op"
            operation_type = Operation.READ
            rate_limit = 50
            requires_approval = False
            parameters = {"count": ParameterSchema("integer", min_value=1)}
            required_params = ["count"]

            def validate(self, arguments):
                return super().validate(arguments)

            def execute(self, api, arguments):
                return {}

            def get_tool_schema(self):
                return {}

        op = TestOp()
        errors = op.validate({"count": 0})
        assert len(errors) > 0
        assert any("must be >=" in e for e in errors)

    def test_max_value_validation_error(self):
        """Test validation catches max value violations."""
        from src.operations import BaseOperationDef

        class TestOp(BaseOperationDef):
            name = "test_op"
            operation_type = Operation.READ
            rate_limit = 50
            requires_approval = False
            parameters = {"count": ParameterSchema("integer", max_value=100)}
            required_params = ["count"]

            def validate(self, arguments):
                return super().validate(arguments)

            def execute(self, api, arguments):
                return {}

            def get_tool_schema(self):
                return {}

        op = TestOp()
        errors = op.validate({"count": 101})
        assert len(errors) > 0
        assert any("must be <=" in e for e in errors)
