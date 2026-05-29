"""Operation and approval gate persistence layer (SQLite)."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.operations import ApprovalGate, ApprovalStatus, OperationRequest, OperationStatus


UTC = timezone.utc


class OperationStore:
    """Persistent store for all operations and approval gates."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize with SQLite database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create connection pool (per-thread is safe)
        self.db_path.touch(exist_ok=True)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    executed_at TEXT,
                    completed_at TEXT,
                    approval_gate_id TEXT,
                    bulk_parent_id TEXT,
                    step_function_arn TEXT,
                    step_function_execution_id TEXT,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS approval_gates (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL UNIQUE,
                    requested_by TEXT NOT NULL,
                    approver TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    approval_timestamp TEXT,
                    reason TEXT,
                    FOREIGN KEY (operation_id) REFERENCES operations(id)
                );

                CREATE INDEX IF NOT EXISTS idx_operations_status ON operations(status);
                CREATE INDEX IF NOT EXISTS idx_operations_created_at ON operations(created_at);
                CREATE INDEX IF NOT EXISTS idx_operations_approval_gate_id ON operations(approval_gate_id);

                CREATE INDEX IF NOT EXISTS idx_approval_gates_status ON approval_gates(status);
                CREATE INDEX IF NOT EXISTS idx_approval_gates_expires_at ON approval_gates(expires_at);
                CREATE INDEX IF NOT EXISTS idx_approval_gates_operation_id ON approval_gates(operation_id);
                """
            )
            conn.commit()
        finally:
            conn.close()

    # Create

    def create_operation(self, op_req: OperationRequest) -> str:
        """Create operation, return operation ID."""
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO operations (
                    id, name, type, status, arguments,
                    created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    op_req.id,
                    op_req.operation_name,
                    op_req.operation_type.value,
                    op_req.status.value,
                    json.dumps(op_req.arguments),
                    op_req.created_at.isoformat(),
                    json.dumps(op_req._metadata),
                ),
            )
            conn.commit()
            return op_req.id
        finally:
            conn.close()

    def create_approval_gate(self, gate: ApprovalGate) -> str:
        """Create approval gate."""
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO approval_gates (
                    id, operation_id, requested_by, status,
                    created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    gate.id,
                    gate.operation_id,
                    gate.requested_by,
                    gate.status.value,
                    gate.created_at.isoformat(),
                    gate.expires_at.isoformat(),
                ),
            )
            conn.commit()
            return gate.id
        finally:
            conn.close()

    # Read

    def get_operation(self, op_id: str) -> OperationRequest | None:
        """Get operation by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM operations WHERE id = ?", (op_id,)
            ).fetchone()
            if not row:
                return None

            op = OperationRequest(
                operation_name=row["name"],
                arguments=json.loads(row["arguments"]),
                operation_type=__import__("src.operations", fromlist=["Operation"]).Operation(
                    row["type"]
                ),
            )
            op.id = row["id"]
            op.status = OperationStatus(row["status"])
            op.created_at = datetime.fromisoformat(row["created_at"])
            if row["executed_at"]:
                op.executed_at = datetime.fromisoformat(row["executed_at"])
            if row["completed_at"]:
                op.completed_at = datetime.fromisoformat(row["completed_at"])
            op.result = json.loads(row["result"]) if row["result"] else None
            op.error = row["error"]
            if row["approval_gate_id"]:
                op.approval_gate = self.get_approval_gate(row["approval_gate_id"])
            op.bulk_parent_id = row["bulk_parent_id"]
            op.step_function_arn = row["step_function_arn"]
            op.step_function_execution_id = row["step_function_execution_id"]
            op._metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            return op
        finally:
            conn.close()

    def get_approval_gate(self, gate_id: str) -> ApprovalGate | None:
        """Get approval gate by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM approval_gates WHERE id = ?", (gate_id,)
            ).fetchone()
            if not row:
                return None

            gate = ApprovalGate(
                operation_id=row["operation_id"],
                requested_by=row["requested_by"],
            )
            gate.id = row["id"]
            gate.status = ApprovalStatus(row["status"])
            gate.created_at = datetime.fromisoformat(row["created_at"])
            gate.expires_at = datetime.fromisoformat(row["expires_at"])
            gate.approver = row["approver"]
            gate.reason = row["reason"]
            if row["approval_timestamp"]:
                gate.approval_timestamp = datetime.fromisoformat(
                    row["approval_timestamp"]
                )

            return gate
        finally:
            conn.close()

    def list_pending_operations(self, limit: int = 100) -> list[OperationRequest]:
        """Get pending operations (for queue processing)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM operations WHERE status = ? ORDER BY created_at ASC LIMIT ?",
                (OperationStatus.PENDING.value, limit),
            ).fetchall()
            return [self._row_to_operation(row) for row in rows]
        finally:
            conn.close()

    def list_pending_approvals(self, limit: int = 100) -> list[ApprovalGate]:
        """Get pending approval gates."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM approval_gates WHERE status = ? ORDER BY created_at ASC LIMIT ?",
                (ApprovalStatus.PENDING.value, limit),
            ).fetchall()
            return [self._row_to_gate(row) for row in rows]
        finally:
            conn.close()

    def list_expired_approvals(self) -> list[ApprovalGate]:
        """Get expired gates (auto-reject)."""
        conn = self._get_conn()
        try:
            now = datetime.now(UTC).isoformat()
            rows = conn.execute(
                "SELECT * FROM approval_gates WHERE status = ? AND expires_at < ?",
                (ApprovalStatus.PENDING.value, now),
            ).fetchall()
            return [self._row_to_gate(row) for row in rows]
        finally:
            conn.close()

    # Update

    def update_operation_status(
        self,
        op_id: str,
        status: OperationStatus,
        result: Any | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update operation status (moving through state machine)."""
        conn = self._get_conn()
        try:
            now = datetime.now(UTC).isoformat()
            executed_at = now if status == OperationStatus.EXECUTING else None
            completed_at = now if status in (
                OperationStatus.COMPLETED,
                OperationStatus.FAILED,
                OperationStatus.CANCELLED,
                OperationStatus.EXPIRED,
            ) else None

            conn.execute(
                """
                UPDATE operations
                SET status = ?, result = ?, error = ?, metadata = ?,
                    executed_at = COALESCE(executed_at, ?),
                    completed_at = COALESCE(completed_at, ?)
                WHERE id = ?
                """,
                (
                    status.value,
                    json.dumps(result) if result else None,
                    error,
                    json.dumps(metadata) if metadata else None,
                    executed_at,
                    completed_at,
                    op_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def update_approval_gate(
        self,
        gate_id: str,
        status: ApprovalStatus,
        approver: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Update approval gate status."""
        conn = self._get_conn()
        try:
            approval_timestamp = None
            if status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
                approval_timestamp = datetime.now(UTC).isoformat()

            conn.execute(
                """
                UPDATE approval_gates
                SET status = ?, approver = ?, reason = ?,
                    approval_timestamp = COALESCE(approval_timestamp, ?)
                WHERE id = ?
                """,
                (status.value, approver, reason, approval_timestamp, gate_id),
            )
            conn.commit()
        finally:
            conn.close()

    # Query

    def get_operation_history(self, op_id: str) -> list[dict[str, Any]]:
        """Get all state transitions for an operation (for debugging)."""
        # TODO: Implement audit table for state transitions
        return []

    def get_approval_history(self, gate_id: str) -> list[dict[str, Any]]:
        """Get all state transitions for approval gate."""
        # TODO: Implement audit table for approval transitions
        return []

    def get_stats(self) -> dict[str, Any]:
        """Get operation statistics (for monitoring)."""
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) as count FROM operations").fetchone()[
                0
            ]
            pending = conn.execute(
                "SELECT COUNT(*) as count FROM operations WHERE status = ?",
                (OperationStatus.PENDING.value,),
            ).fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) as count FROM operations WHERE status = ?",
                (OperationStatus.COMPLETED.value,),
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) as count FROM operations WHERE status = ?",
                (OperationStatus.FAILED.value,),
            ).fetchone()[0]
            pending_approvals = conn.execute(
                "SELECT COUNT(*) as count FROM approval_gates WHERE status = ?",
                (ApprovalStatus.PENDING.value,),
            ).fetchone()[0]

            # Average execution time (for completed operations)
            avg_exec = conn.execute(
                """
                SELECT AVG(
                    (julianday(completed_at) - julianday(executed_at)) * 1000 * 60 * 60
                ) as avg_ms
                FROM operations
                WHERE status = ? AND executed_at IS NOT NULL AND completed_at IS NOT NULL
                """,
                (OperationStatus.COMPLETED.value,),
            ).fetchone()[0]

            return {
                "total_operations": total,
                "pending": pending,
                "completed": completed,
                "failed": failed,
                "pending_approvals": pending_approvals,
                "average_execution_time_ms": int(avg_exec) if avg_exec else 0,
            }
        finally:
            conn.close()

    # Cleanup

    def expire_old_operations(
        self, older_than: timedelta = timedelta(days=30)
    ) -> int:
        """Archive operations older than TTL, return count."""
        conn = self._get_conn()
        try:
            cutoff = (datetime.now(UTC) - older_than).isoformat()
            cursor = conn.execute(
                "DELETE FROM operations WHERE created_at < ?", (cutoff,)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # Helpers

    def _row_to_operation(self, row: sqlite3.Row) -> OperationRequest:
        """Convert database row to OperationRequest."""
        from src.operations import Operation

        op = OperationRequest(
            operation_name=row["name"],
            arguments=json.loads(row["arguments"]),
            operation_type=Operation(row["type"]),
        )
        op.id = row["id"]
        op.status = OperationStatus(row["status"])
        op.created_at = datetime.fromisoformat(row["created_at"])
        if row["executed_at"]:
            op.executed_at = datetime.fromisoformat(row["executed_at"])
        if row["completed_at"]:
            op.completed_at = datetime.fromisoformat(row["completed_at"])
        op.result = json.loads(row["result"]) if row["result"] else None
        op.error = row["error"]
        if row["approval_gate_id"]:
            op.approval_gate = self.get_approval_gate(row["approval_gate_id"])
        op.bulk_parent_id = row["bulk_parent_id"]
        op.step_function_arn = row["step_function_arn"]
        op.step_function_execution_id = row["step_function_execution_id"]
        op._metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        return op

    def _row_to_gate(self, row: sqlite3.Row) -> ApprovalGate:
        """Convert database row to ApprovalGate."""
        gate = ApprovalGate(
            operation_id=row["operation_id"],
            requested_by=row["requested_by"],
        )
        gate.id = row["id"]
        gate.status = ApprovalStatus(row["status"])
        gate.created_at = datetime.fromisoformat(row["created_at"])
        gate.expires_at = datetime.fromisoformat(row["expires_at"])
        gate.approver = row["approver"]
        gate.reason = row["reason"]
        if row["approval_timestamp"]:
            gate.approval_timestamp = datetime.fromisoformat(row["approval_timestamp"])

        return gate
