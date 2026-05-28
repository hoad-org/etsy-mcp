"""Tests for Etsy MCP Server."""

from unittest.mock import Mock, patch
from src.server import EtsyMCPServer


class TestEtsyMCPServer:
    """Test Etsy MCP Server."""

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_server_initialization(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test that server can be initialized."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        server = EtsyMCPServer()
        assert server.config is not None
        assert server.audit is not None
        assert server.guardrails is not None
        assert server.etsy is not None

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_list_tools(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test listing available tools."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        server = EtsyMCPServer()
        tools = server.list_tools()

        assert "tools" in tools
        assert len(tools["tools"]) == 4
        assert tools["tools"][0]["name"] == "get_shop_info"

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_call_tool_get_shop_info(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test calling get_shop_info tool."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = True
        mock_guardrails.return_value = mock_guardrails_instance

        mock_etsy_instance = Mock()
        mock_etsy_instance.get_shop.return_value = {"shop_id": 123456, "shop_name": "Test Shop"}
        mock_etsy.return_value = mock_etsy_instance

        server = EtsyMCPServer()
        result = server.call_tool("get_shop_info", {})

        assert "result" in result
        assert result["result"]["shop_id"] == 123456

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_call_tool_rate_limited(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test that rate limiting is enforced."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = False
        mock_guardrails.return_value = mock_guardrails_instance

        server = EtsyMCPServer()
        result = server.call_tool("get_shop_info", {})

        assert "error" in result
        assert result["error"] == "Rate limit exceeded"

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_call_tool_invalid_name(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test calling invalid tool."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = True
        mock_guardrails.return_value = mock_guardrails_instance

        server = EtsyMCPServer()
        result = server.call_tool("invalid_tool", {})

        assert "error" in result

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_call_tool_missing_required_param(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test calling tool with missing required parameter."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = True
        mock_guardrails.return_value = mock_guardrails_instance

        server = EtsyMCPServer()
        result = server.call_tool("get_product", {})

        assert "error" in result
        assert "listing_id is required" in result["error"]

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_call_tool_list_products(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test calling list_products tool."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = True
        mock_guardrails.return_value = mock_guardrails_instance

        mock_etsy_instance = Mock()
        mock_etsy_instance.list_products.return_value = {
            "listings": [{"listing_id": 1, "title": "Product 1"}],
            "count": 1,
            "pagination": {"offset": 0, "limit": 20}
        }
        mock_etsy.return_value = mock_etsy_instance

        server = EtsyMCPServer()
        result = server.call_tool("list_products", {"status": "active", "limit": 20, "offset": 0})

        assert "result" in result
        assert len(result["result"]["listings"]) == 1

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_call_tool_get_product(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test calling get_product tool."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = True
        mock_guardrails.return_value = mock_guardrails_instance

        mock_etsy_instance = Mock()
        mock_etsy_instance.get_product.return_value = {"listing_id": 1, "title": "Product 1"}
        mock_etsy.return_value = mock_etsy_instance

        server = EtsyMCPServer()
        result = server.call_tool("get_product", {"listing_id": 1})

        assert "result" in result
        assert result["result"]["listing_id"] == 1

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_call_tool_list_orders(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test calling list_orders tool."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = True
        mock_guardrails.return_value = mock_guardrails_instance

        mock_etsy_instance = Mock()
        mock_etsy_instance.list_orders.return_value = {
            "orders": [{"order_id": 1, "amount": "100.00"}],
            "count": 1,
            "pagination": {"offset": 0, "limit": 20}
        }
        mock_etsy.return_value = mock_etsy_instance

        server = EtsyMCPServer()
        result = server.call_tool("list_orders", {"limit": 20, "offset": 0})

        assert "result" in result
        assert len(result["result"]["orders"]) == 1

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_call_tool_api_error(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test handling API errors."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = True
        mock_guardrails.return_value = mock_guardrails_instance

        mock_etsy_instance = Mock()
        mock_etsy_instance.get_shop.side_effect = Exception("API Error")
        mock_etsy.return_value = mock_etsy_instance

        server = EtsyMCPServer()
        result = server.call_tool("get_shop_info", {})

        assert "error" in result

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_handle_request_list_tools(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test handling list_tools request."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        server = EtsyMCPServer()
        response = server.handle_request({"method": "list_tools"})

        assert "tools" in response
        assert len(response["tools"]) == 4

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_handle_request_call_tool(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test handling call_tool request."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        mock_guardrails_instance = Mock()
        mock_guardrails_instance.check_read.return_value = True
        mock_guardrails.return_value = mock_guardrails_instance

        mock_etsy_instance = Mock()
        mock_etsy_instance.get_shop.return_value = {"shop_id": 123456}
        mock_etsy.return_value = mock_etsy_instance

        server = EtsyMCPServer()
        response = server.handle_request({
            "method": "call_tool",
            "name": "get_shop_info",
            "arguments": {}
        })

        assert "result" in response
        assert response["result"]["shop_id"] == 123456

    @patch('src.server.Config.load')
    @patch('src.server.AuditLogger')
    @patch('src.server.Guardrails')
    @patch('src.server.CryptoManager.decrypt')
    @patch('src.server.EtsyAPI')
    def test_handle_request_unknown_method(self, mock_etsy, mock_decrypt, mock_guardrails, mock_audit, mock_config):
        """Test handling unknown method."""
        mock_config.return_value = Mock(
            audit_log_dir="~/.etsy-mcp/audit/",
            read_rate_limit=50,
            write_rate_limit=5,
            dangerous_rate_limit=1,
            etsy_api_key="encrypted-key",
            vault_password="password",
            etsy_shop_id="123456"
        )
        mock_decrypt.return_value = "decrypted-key"

        server = EtsyMCPServer()
        response = server.handle_request({"method": "unknown_method"})

        assert "error" in response
        assert "Unknown method" in response["error"]
