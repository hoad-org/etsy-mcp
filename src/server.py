"""Etsy MCP Server - MCP protocol implementation with operation registry."""

import json
import sys
from typing import Any

from src.audit import AuditLogger
from src.config import Config
from src.crypto import CryptoManager
from src.etsy_api import EtsyAPI
from src.guardrails import Guardrails
from src.operations import Operation, OperationRequest
from src.operation_registry import REGISTRY

# Import tools to populate registry
import src.tools  # noqa: F401


class EtsyMCPServer:
    """MCP server for Etsy store management with operation registry."""

    def __init__(self) -> None:
        """Initialize MCP server."""
        self.config = Config.load()
        self.audit = AuditLogger(self.config.audit_log_dir)
        self.guardrails = Guardrails(
            read_rate_limit=self.config.read_rate_limit,
            write_rate_limit=self.config.write_rate_limit,
            dangerous_rate_limit=self.config.dangerous_rate_limit,
        )

        # Decrypt and initialize API client
        self.api_key = CryptoManager.decrypt(self.config.etsy_api_key, self.config.vault_password)
        self.etsy = EtsyAPI(self.api_key, self.config.etsy_shop_id)

    def list_tools(self) -> dict[str, Any]:
        """Return list of available tools (generated from registry)."""
        return {"tools": REGISTRY.get_tool_schemas()}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool (single dispatch point using registry)."""
        # Get operation definition
        op_def = REGISTRY.get(name)
        if not op_def:
            return {"error": f"Unknown tool: {name}"}

        # Validate arguments
        errors = op_def.validate(arguments)
        if errors:
            self.audit.log(
                name,
                {"status": "validation_failed", "errors": errors},
                redact=["api_token", "password"],
            )
            return {"error": f"Validation failed: {'; '.join(errors)}"}

        # Create operation request
        op_req = OperationRequest(
            operation_name=name,
            arguments=arguments,
            operation_type=op_def.operation_type,
        )

        try:
            if op_def.operation_type == Operation.READ:
                return self._execute_read(op_def, op_req)
            elif op_def.operation_type == Operation.WRITE:
                return self._execute_write_pending(op_def, op_req)
            elif op_def.operation_type == Operation.BULK:
                return self._execute_bulk_pending(op_def, op_req)
            elif op_def.operation_type == Operation.ORCHESTRATED:
                return self._execute_orchestrated_pending(op_def, op_req)
            else:
                return {"error": f"Unknown operation type: {op_def.operation_type}"}

        except Exception as e:
            self.guardrails.record_error()
            self.audit.log(
                name,
                {"status": "error", "error": str(e)},
                redact=["api_token", "password"],
            )
            return {"error": str(e)}

    def _execute_read(self, op_def: Any, op_req: OperationRequest) -> dict[str, Any]:
        """Execute P1 read-only operation (immediate)."""
        # Check rate limits
        if not self.guardrails.check_read():
            self.audit.log(
                op_req.operation_name,
                {"status": "rate_limit_exceeded", "operation_type": "read"},
            )
            return {"error": "Rate limit exceeded for read operations"}

        # Execute immediately
        result = op_def.execute(self.etsy, op_req.arguments)
        self.guardrails.record_success()

        # Log successful execution
        self.audit.log(
            op_req.operation_name,
            {
                "status": "success",
                "operation_type": "read",
                "shop_id": self.config.etsy_shop_id,
            },
        )

        return {"result": result}

    def _execute_write_pending(self, op_def: Any, op_req: OperationRequest) -> dict[str, Any]:
        """Queue P2 write operation (pending approval)."""
        # Check rate limits
        if not self.guardrails.check_write():
            self.audit.log(
                op_req.operation_name,
                {"status": "rate_limit_exceeded", "operation_type": "write"},
            )
            return {"error": "Rate limit exceeded for write operations"}

        # Log pending operation
        self.audit.log(
            op_req.operation_name,
            {
                "status": "pending_approval",
                "operation_type": "write",
                "operation_id": op_req.id,
                "shop_id": self.config.etsy_shop_id,
            },
        )

        # In Phase 1 (without async queue), we return that approval is required
        return {
            "status": "pending_approval",
            "operation_id": op_req.id,
            "operation_type": "write",
            "message": "This operation requires approval before execution",
            "details": {
                "operation_name": op_req.operation_name,
                "arguments": op_req.arguments,
            },
        }

    def _execute_bulk_pending(self, op_def: Any, op_req: OperationRequest) -> dict[str, Any]:
        """Queue P3 bulk operation (pending approval)."""
        # Check rate limits
        if not self.guardrails.check_write():
            self.audit.log(
                op_req.operation_name,
                {"status": "rate_limit_exceeded", "operation_type": "bulk"},
            )
            return {"error": "Rate limit exceeded for bulk operations"}

        # Log pending bulk operation
        self.audit.log(
            op_req.operation_name,
            {
                "status": "pending_approval",
                "operation_type": "bulk",
                "operation_id": op_req.id,
                "shop_id": self.config.etsy_shop_id,
            },
        )

        # In Phase 1, bulk operations also require approval
        return {
            "status": "pending_approval",
            "operation_id": op_req.id,
            "operation_type": "bulk",
            "message": "This bulk operation requires approval before execution",
            "details": {
                "operation_name": op_req.operation_name,
                "arguments": op_req.arguments,
            },
        }

    def _execute_orchestrated_pending(self, op_def: Any, op_req: OperationRequest) -> dict[str, Any]:
        """Queue P4 orchestrated operation (pending approval)."""
        # Check rate limits (use dangerous limit)
        if not self.guardrails.check_dangerous():
            self.audit.log(
                op_req.operation_name,
                {"status": "rate_limit_exceeded", "operation_type": "orchestrated"},
            )
            return {"error": "Rate limit exceeded for orchestrated operations"}

        # Log pending orchestrated operation
        self.audit.log(
            op_req.operation_name,
            {
                "status": "pending_approval",
                "operation_type": "orchestrated",
                "operation_id": op_req.id,
                "shop_id": self.config.etsy_shop_id,
            },
        )

        # P4 operations require approval
        return {
            "status": "pending_approval",
            "operation_id": op_req.id,
            "operation_type": "orchestrated",
            "message": "This orchestrated operation requires approval before execution",
            "details": {
                "operation_name": op_req.operation_name,
                "arguments": op_req.arguments,
            },
        }

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP protocol request."""
        method = request.get("method")

        if method == "list_tools":
            return self.list_tools()
        elif method == "call_tool":
            tool_name: str | None = request.get("name")
            arguments = request.get("arguments", {})
            if tool_name is None:
                return {"error": "Missing tool name"}
            return self.call_tool(tool_name, arguments)
        else:
            return {"error": f"Unknown method: {method}"}


def main() -> None:
    """Main entry point for MCP server."""
    server = EtsyMCPServer()

    # Read requests from stdin (MCP protocol)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {e}"}))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
