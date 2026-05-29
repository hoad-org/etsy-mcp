"""Tests for OperationStore persistence layer."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.operation_store import OperationStore
from src.operations import ApprovalGate, ApprovalStatus, Operation, OperationRequest, OperationStatus


UTC = timezone.utc


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield str(db_path)


class TestOperationStore:
    """Test OperationStore class."""

    def test_init_creates_database(self, temp_db):
        """Test that __init__ creates database and schema."""
        OperationStore(temp_db)
        assert Path(temp_db).exists()

    def test_create_operation(self, temp_db):
        """Test creating an operation."""
        store = OperationStore(temp_db)
        op_req = OperationRequest(
            operation_name="test_op",
            arguments={"key": "value"},
            operation_type=Operation.READ
        )
        op_id = store.create_operation(op_req)
        assert op_id == op_req.id
        assert op_id is not None

    def test_get_operation(self, temp_db):
        """Test retrieving an operation."""
        store = OperationStore(temp_db)
        op_req = OperationRequest(
            operation_name="test_op",
            arguments={"key": "value"},
            operation_type=Operation.READ
        )
        store.create_operation(op_req)

        retrieved = store.get_operation(op_req.id)
        assert retrieved is not None
        assert retrieved.operation_name == "test_op"
        assert retrieved.arguments == {"key": "value"}
        assert retrieved.status == OperationStatus.PENDING

    def test_get_operation_not_found(self, temp_db):
        """Test retrieving non-existent operation."""
        store = OperationStore(temp_db)
        retrieved = store.get_operation("nonexistent")
        assert retrieved is None

    def test_create_approval_gate(self, temp_db):
        """Test creating an approval gate."""
        store = OperationStore(temp_db)
        gate = ApprovalGate(
            operation_id="op-123",
            requested_by="user@example.com"
        )
        gate_id = store.create_approval_gate(gate)
        assert gate_id == gate.id

    def test_get_approval_gate(self, temp_db):
        """Test retrieving an approval gate."""
        store = OperationStore(temp_db)
        gate = ApprovalGate(
            operation_id="op-123",
            requested_by="user@example.com"
        )
        store.create_approval_gate(gate)

        retrieved = store.get_approval_gate(gate.id)
        assert retrieved is not None
        assert retrieved.operation_id == "op-123"
        assert retrieved.requested_by == "user@example.com"
        assert retrieved.status == ApprovalStatus.PENDING

    def test_get_approval_gate_not_found(self, temp_db):
        """Test retrieving non-existent gate."""
        store = OperationStore(temp_db)
        retrieved = store.get_approval_gate("nonexistent")
        assert retrieved is None

    def test_update_operation_status_to_executing(self, temp_db):
        """Test updating operation to EXECUTING status."""
        store = OperationStore(temp_db)
        op_req = OperationRequest(
            operation_name="test_op",
            arguments={},
            operation_type=Operation.READ
        )
        store.create_operation(op_req)

        store.update_operation_status(op_req.id, OperationStatus.EXECUTING)
        retrieved = store.get_operation(op_req.id)
        assert retrieved.status == OperationStatus.EXECUTING
        assert retrieved.executed_at is not None

    def test_update_operation_status_to_completed(self, temp_db):
        """Test updating operation to COMPLETED status."""
        store = OperationStore(temp_db)
        op_req = OperationRequest(
            operation_name="test_op",
            arguments={},
            operation_type=Operation.READ
        )
        store.create_operation(op_req)

        result = {"data": "result"}
        store.update_operation_status(op_req.id, OperationStatus.COMPLETED, result=result)
        retrieved = store.get_operation(op_req.id)
        assert retrieved.status == OperationStatus.COMPLETED
        assert retrieved.result == result
        assert retrieved.completed_at is not None

    def test_update_operation_status_to_failed(self, temp_db):
        """Test updating operation to FAILED status."""
        store = OperationStore(temp_db)
        op_req = OperationRequest(
            operation_name="test_op",
            arguments={},
            operation_type=Operation.READ
        )
        store.create_operation(op_req)

        store.update_operation_status(op_req.id, OperationStatus.FAILED, error="Test error")
        retrieved = store.get_operation(op_req.id)
        assert retrieved.status == OperationStatus.FAILED
        assert retrieved.error == "Test error"
        assert retrieved.completed_at is not None

    def test_update_approval_gate_to_approved(self, temp_db):
        """Test updating approval gate to APPROVED."""
        store = OperationStore(temp_db)
        gate = ApprovalGate(
            operation_id="op-123",
            requested_by="user@example.com"
        )
        store.create_approval_gate(gate)

        store.update_approval_gate(gate.id, ApprovalStatus.APPROVED, approver="approver@example.com")
        retrieved = store.get_approval_gate(gate.id)
        assert retrieved.status == ApprovalStatus.APPROVED
        assert retrieved.approver == "approver@example.com"
        assert retrieved.approval_timestamp is not None

    def test_update_approval_gate_to_rejected(self, temp_db):
        """Test updating approval gate to REJECTED."""
        store = OperationStore(temp_db)
        gate = ApprovalGate(
            operation_id="op-123",
            requested_by="user@example.com"
        )
        store.create_approval_gate(gate)

        store.update_approval_gate(gate.id, ApprovalStatus.REJECTED, reason="Not approved")
        retrieved = store.get_approval_gate(gate.id)
        assert retrieved.status == ApprovalStatus.REJECTED
        assert retrieved.reason == "Not approved"

    def test_list_pending_operations(self, temp_db):
        """Test listing pending operations."""
        store = OperationStore(temp_db)
        op1 = OperationRequest("op1", {}, Operation.READ)
        op2 = OperationRequest("op2", {}, Operation.WRITE)
        store.create_operation(op1)
        store.create_operation(op2)

        # Mark op2 as completed
        store.update_operation_status(op2.id, OperationStatus.COMPLETED)

        pending = store.list_pending_operations()
        assert len(pending) == 1
        assert pending[0].operation_name == "op1"

    def test_list_pending_approvals(self, temp_db):
        """Test listing pending approvals."""
        store = OperationStore(temp_db)
        gate1 = ApprovalGate("op1", "user1@example.com")
        gate2 = ApprovalGate("op2", "user2@example.com")
        store.create_approval_gate(gate1)
        store.create_approval_gate(gate2)

        # Approve gate2
        store.update_approval_gate(gate2.id, ApprovalStatus.APPROVED)

        pending = store.list_pending_approvals()
        assert len(pending) == 1
        assert pending[0].operation_id == "op1"

    def test_list_expired_approvals(self, temp_db):
        """Test listing expired approvals."""
        store = OperationStore(temp_db)
        gate = ApprovalGate("op1", "user@example.com")
        store.create_approval_gate(gate)

        # Set expires_at to past
        from datetime import datetime, timezone
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        conn = store._get_conn()
        try:
            conn.execute(
                "UPDATE approval_gates SET expires_at = ? WHERE id = ?",
                (past, gate.id)
            )
            conn.commit()
        finally:
            conn.close()

        expired = store.list_expired_approvals()
        assert len(expired) == 1
        assert expired[0].id == gate.id

    def test_get_stats(self, temp_db):
        """Test getting operation statistics."""
        store = OperationStore(temp_db)
        op1 = OperationRequest("op1", {}, Operation.READ)
        op2 = OperationRequest("op2", {}, Operation.READ)
        store.create_operation(op1)
        store.create_operation(op2)

        # Mark op2 as completed
        store.update_operation_status(op2.id, OperationStatus.COMPLETED, result={"data": "test"})

        stats = store.get_stats()
        assert stats["total_operations"] == 2
        assert stats["pending"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 0

    def test_expire_old_operations(self, temp_db):
        """Test expiring old operations."""
        store = OperationStore(temp_db)
        op = OperationRequest("op1", {}, Operation.READ)
        store.create_operation(op)

        # Set created_at to past
        past = (datetime.now(UTC) - timedelta(days=31)).isoformat()
        conn = store._get_conn()
        try:
            conn.execute(
                "UPDATE operations SET created_at = ? WHERE id = ?",
                (past, op.id)
            )
            conn.commit()
        finally:
            conn.close()

        # Should expire operations older than 30 days
        count = store.expire_old_operations(timedelta(days=30))
        assert count == 1

        # Verify it's gone
        retrieved = store.get_operation(op.id)
        assert retrieved is None

    def test_operation_metadata(self, temp_db):
        """Test operation metadata persistence."""
        store = OperationStore(temp_db)
        op = OperationRequest("op1", {}, Operation.READ)
        op._metadata = {"custom_key": "custom_value", "retry_count": 2}
        store.create_operation(op)

        retrieved = store.get_operation(op.id)
        assert retrieved._metadata["custom_key"] == "custom_value"
        assert retrieved._metadata["retry_count"] == 2
