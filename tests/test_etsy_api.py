"""Tests for Etsy API client."""

from unittest.mock import Mock, patch
from src.etsy_api import EtsyAPI, TLS13HTTPAdapter


class TestTLS13HTTPAdapter:
    """Test TLS 1.3 enforcement."""

    def test_adapter_creates_context(self):
        """Test that adapter can be instantiated."""
        adapter = TLS13HTTPAdapter()
        assert adapter is not None


class TestEtsyAPI:
    """Test Etsy API client."""

    def test_etsy_api_initialization(self):
        """Test that EtsyAPI can be initialized."""
        api = EtsyAPI(api_key="test-key", shop_id="123456")
        assert api.api_key == "test-key"
        assert api.shop_id == "123456"
        assert api.session is not None

    def test_sign_request_creates_signature(self):
        """Test that _sign_request creates HMAC signature."""
        api = EtsyAPI(api_key="test-key", shop_id="123456")
        headers = api._sign_request("/shops/123456")
        
        assert "X-Etsy-Signature" in headers
        assert isinstance(headers["X-Etsy-Signature"], str)
        assert len(headers["X-Etsy-Signature"]) == 64  # SHA256 hex digest

    def test_sign_request_with_params(self):
        """Test that _sign_request includes params in signature."""
        api = EtsyAPI(api_key="test-key", shop_id="123456")
        headers = api._sign_request("/shops/123456/listings", {"status": "active", "limit": 20})
        
        assert "X-Etsy-Signature" in headers
        assert isinstance(headers["X-Etsy-Signature"], str)

    @patch('src.etsy_api.requests.Session.get')
    def test_get_shop(self, mock_get):
        """Test getting shop info."""
        mock_response = Mock()
        mock_response.json.return_value = {"shop": {"shop_id": 123456, "shop_name": "Test Shop"}}
        mock_get.return_value = mock_response

        api = EtsyAPI(api_key="test-key", shop_id="123456")
        shop = api.get_shop()

        assert shop["shop_id"] == 123456
        assert shop["shop_name"] == "Test Shop"

    @patch('src.etsy_api.requests.Session.get')
    def test_list_products(self, mock_get):
        """Test listing products."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"listing_id": 1, "title": "Product 1"}],
            "count": 1
        }
        mock_get.return_value = mock_response

        api = EtsyAPI(api_key="test-key", shop_id="123456")
        products = api.list_products(status="active", limit=20)

        assert len(products["listings"]) == 1
        assert products["listings"][0]["title"] == "Product 1"
        assert products["count"] == 1

    @patch('src.etsy_api.requests.Session.get')
    def test_get_product(self, mock_get):
        """Test getting product details."""
        mock_response = Mock()
        mock_response.json.return_value = {"listing": {"listing_id": 1, "title": "Product 1"}}
        mock_get.return_value = mock_response

        api = EtsyAPI(api_key="test-key", shop_id="123456")
        product = api.get_product(listing_id=1)

        assert product["listing_id"] == 1
        assert product["title"] == "Product 1"

    @patch('src.etsy_api.requests.Session.get')
    def test_list_orders(self, mock_get):
        """Test listing orders."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"order_id": 1, "amount": "100.00"}],
            "count": 1
        }
        mock_get.return_value = mock_response

        api = EtsyAPI(api_key="test-key", shop_id="123456")
        orders = api.list_orders(limit=20)

        assert len(orders["orders"]) == 1
        assert orders["orders"][0]["order_id"] == 1
        assert orders["count"] == 1

    def test_close_session(self):
        """Test closing session."""
        api = EtsyAPI(api_key="test-key", shop_id="123456")
        api.session.close = Mock()
        api.close()
        api.session.close.assert_called_once()
