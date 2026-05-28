"""Etsy MCP Server - MCP protocol implementation."""

import json
from typing import Any
import sys

from src.config import Config
from src.crypto import CryptoManager
from src.audit import AuditLogger
from src.etsy_api import EtsyAPI
from src.guardrails import Guardrails


class EtsyMCPServer:
    """MCP server for Etsy store management."""

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
        """Return list of available tools."""
        return {
            "tools": [
                {
                    "name": "get_shop_info",
                    "description": "Get shop information (read-only)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
                {
                    "name": "list_products",
                    "description": "List products from shop (read-only)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Product status (active, draft, sold_out)",
                                "default": "active",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max results (1-100)",
                                "default": 20,
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Pagination offset",
                                "default": 0,
                            },
                        },
                        "required": [],
                    },
                },
                {
                    "name": "get_product",
                    "description": "Get product details (read-only)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "listing_id": {
                                "type": "integer",
                                "description": "Product listing ID",
                            },
                        },
                        "required": ["listing_id"],
                    },
                },
                {
                    "name": "list_orders",
                    "description": "List recent orders (read-only)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Max results (1-100)",
                                "default": 20,
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Pagination offset",
                                "default": 0,
                            },
                        },
                        "required": [],
                    },
                },
            ]
        }

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool."""
        # Check rate limits
        if not self.guardrails.check_read():
            self.audit.log("rate_limit_exceeded", {"tool": name}, redact=["api_token"])
            return {"error": "Rate limit exceeded"}

        try:
            if name == "get_shop_info":
                result = self.etsy.get_shop()
                self.guardrails.record_success()
                self.audit.log(name, {"status": "success", "shop_id": self.config.etsy_shop_id})
                return {"result": result}

            elif name == "list_products":
                status = arguments.get("status", "active")
                limit = arguments.get("limit", 20)
                offset = arguments.get("offset", 0)

                result = self.etsy.list_products(status=status, limit=limit, offset=offset)
                self.guardrails.record_success()
                self.audit.log(
                    name,
                    {
                        "status": "success",
                        "status_filter": status,
                        "limit": limit,
                        "offset": offset,
                        "results_count": len(result.get("listings", [])),
                    },
                )
                return {"result": result}

            elif name == "get_product":
                listing_id = arguments.get("listing_id")
                if not listing_id:
                    return {"error": "listing_id is required"}

                result = self.etsy.get_product(listing_id)
                self.guardrails.record_success()
                self.audit.log(name, {"status": "success", "listing_id": listing_id})
                return {"result": result}

            elif name == "list_orders":
                limit = arguments.get("limit", 20)
                offset = arguments.get("offset", 0)

                result = self.etsy.list_orders(limit=limit, offset=offset)
                self.guardrails.record_success()
                self.audit.log(
                    name,
                    {
                        "status": "success",
                        "limit": limit,
                        "offset": offset,
                        "results_count": len(result.get("orders", [])),
                    },
                )
                return {"result": result}

            else:
                return {"error": f"Unknown tool: {name}"}

        except Exception as e:
            self.guardrails.record_error()
            self.audit.log(name, {"status": "error", "error": str(e)})
            return {"error": str(e)}

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP protocol request."""
        method = request.get("method")

        if method == "list_tools":
            return self.list_tools()
        elif method == "call_tool":
            tool_name = request.get("name")
            arguments = request.get("arguments", {})
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
