"""Tests for P1 (read-only) operations."""

from unittest.mock import Mock

from src.tools.p1_read import (
    GetListingInventoryOperation,
    GetListingOperation,
    GetOrderOperation,
    GetShopInfoOperation,
    ListListingsOperation,
    ListOrdersOperation,
)


class TestGetShopInfoOperation:
    """Test GetShopInfoOperation."""

    def test_no_parameters_required(self):
        """Test that get_shop_info requires no parameters."""
        op = GetShopInfoOperation()
        errors = op.validate({})
        assert len(errors) == 0

    def test_execute_calls_api(self):
        """Test execute calls api.get_shop()."""
        op = GetShopInfoOperation()
        api = Mock()
        api.get_shop.return_value = {"shop_id": "123"}

        result = op.execute(api, {})

        api.get_shop.assert_called_once()
        assert result == {"shop_id": "123"}


class TestListListingsOperation:
    """Test ListListingsOperation."""

    def test_validate_default_parameters(self):
        """Test validation with no parameters uses defaults."""
        op = ListListingsOperation()
        errors = op.validate({})
        assert len(errors) == 0

    def test_validate_invalid_limit_too_low(self):
        """Test validation rejects limit < 1."""
        op = ListListingsOperation()
        errors = op.validate({"limit": 0})
        assert len(errors) > 0
        assert any("limit" in e for e in errors)

    def test_validate_invalid_limit_too_high(self):
        """Test validation rejects limit > 100."""
        op = ListListingsOperation()
        errors = op.validate({"limit": 101})
        assert len(errors) > 0
        assert any("limit" in e for e in errors)

    def test_validate_invalid_offset_negative(self):
        """Test validation rejects negative offset."""
        op = ListListingsOperation()
        errors = op.validate({"offset": -1})
        assert len(errors) > 0
        assert any("offset" in e for e in errors)

    def test_validate_valid_limit_boundaries(self):
        """Test validation accepts limit at boundaries."""
        op = ListListingsOperation()
        errors = op.validate({"limit": 1})
        assert len(errors) == 0

        errors = op.validate({"limit": 100})
        assert len(errors) == 0

    def test_validate_valid_offset(self):
        """Test validation accepts valid offset."""
        op = ListListingsOperation()
        errors = op.validate({"offset": 0})
        assert len(errors) == 0

        errors = op.validate({"offset": 50})
        assert len(errors) == 0

    def test_execute_calls_api_with_defaults(self):
        """Test execute passes default values to API."""
        op = ListListingsOperation()
        api = Mock()
        api.list_listings.return_value = {"listings": []}

        op.execute(api, {})

        api.list_listings.assert_called_once_with(
            status="active",
            limit=20,
            offset=0,
            sort_by="created",
        )

    def test_execute_calls_api_with_parameters(self):
        """Test execute passes provided parameters to API."""
        op = ListListingsOperation()
        api = Mock()
        api.list_listings.return_value = {"listings": []}

        op.execute(
            api,
            {
                "status": "sold_out",
                "limit": 50,
                "offset": 100,
                "sort_by": "price",
            },
        )

        api.list_listings.assert_called_once_with(
            status="sold_out",
            limit=50,
            offset=100,
            sort_by="price",
        )


class TestGetListingOperation:
    """Test GetListingOperation."""

    def test_validate_missing_listing_id(self):
        """Test validation requires listing_id."""
        op = GetListingOperation()
        errors = op.validate({})
        assert len(errors) > 0
        assert any("listing_id" in e for e in errors)

    def test_validate_invalid_listing_id_not_integer(self):
        """Test validation rejects non-integer listing_id."""
        op = GetListingOperation()
        errors = op.validate({"listing_id": "abc"})
        assert len(errors) > 0
        assert any("listing_id" in e for e in errors)

    def test_validate_invalid_listing_id_zero(self):
        """Test validation rejects listing_id < 1."""
        op = GetListingOperation()
        errors = op.validate({"listing_id": 0})
        assert len(errors) > 0
        assert any("listing_id" in e for e in errors)

    def test_validate_invalid_listing_id_negative(self):
        """Test validation rejects negative listing_id."""
        op = GetListingOperation()
        errors = op.validate({"listing_id": -1})
        assert len(errors) > 0
        assert any("listing_id" in e for e in errors)

    def test_validate_valid_listing_id(self):
        """Test validation accepts valid listing_id."""
        op = GetListingOperation()
        errors = op.validate({"listing_id": 1})
        assert len(errors) == 0

    def test_execute_calls_api(self):
        """Test execute calls api.get_listing()."""
        op = GetListingOperation()
        api = Mock()
        api.get_listing.return_value = {"listing_id": 123, "title": "Product"}

        result = op.execute(api, {"listing_id": 123})

        api.get_listing.assert_called_once_with(123)
        assert result == {"listing_id": 123, "title": "Product"}


class TestGetListingInventoryOperation:
    """Test GetListingInventoryOperation."""

    def test_validate_missing_listing_id(self):
        """Test validation requires listing_id."""
        op = GetListingInventoryOperation()
        errors = op.validate({})
        assert len(errors) > 0
        assert any("listing_id" in e for e in errors)

    def test_validate_invalid_listing_id_not_integer(self):
        """Test validation rejects non-integer listing_id."""
        op = GetListingInventoryOperation()
        errors = op.validate({"listing_id": "abc"})
        assert len(errors) > 0
        assert any("listing_id" in e for e in errors)

    def test_validate_invalid_listing_id_zero(self):
        """Test validation rejects listing_id < 1."""
        op = GetListingInventoryOperation()
        errors = op.validate({"listing_id": 0})
        assert len(errors) > 0
        assert any("listing_id" in e for e in errors)

    def test_validate_invalid_listing_id_negative(self):
        """Test validation rejects negative listing_id."""
        op = GetListingInventoryOperation()
        errors = op.validate({"listing_id": -1})
        assert len(errors) > 0
        assert any("listing_id" in e for e in errors)

    def test_validate_valid_listing_id(self):
        """Test validation accepts valid listing_id."""
        op = GetListingInventoryOperation()
        errors = op.validate({"listing_id": 1})
        assert len(errors) == 0

    def test_execute_calls_api(self):
        """Test execute calls api.get_listing_inventory()."""
        op = GetListingInventoryOperation()
        api = Mock()
        api.get_listing_inventory.return_value = {"inventory": []}

        result = op.execute(api, {"listing_id": 123})

        api.get_listing_inventory.assert_called_once_with(123)
        assert result == {"inventory": []}


class TestListOrdersOperation:
    """Test ListOrdersOperation."""

    def test_validate_default_parameters(self):
        """Test validation with no parameters uses defaults."""
        op = ListOrdersOperation()
        errors = op.validate({})
        assert len(errors) == 0

    def test_validate_invalid_limit_too_low(self):
        """Test validation rejects limit < 1."""
        op = ListOrdersOperation()
        errors = op.validate({"limit": 0})
        assert len(errors) > 0
        assert any("limit" in e for e in errors)

    def test_validate_invalid_limit_too_high(self):
        """Test validation rejects limit > 100."""
        op = ListOrdersOperation()
        errors = op.validate({"limit": 101})
        assert len(errors) > 0
        assert any("limit" in e for e in errors)

    def test_validate_invalid_offset_negative(self):
        """Test validation rejects negative offset."""
        op = ListOrdersOperation()
        errors = op.validate({"offset": -1})
        assert len(errors) > 0
        assert any("offset" in e for e in errors)

    def test_validate_valid_limit_boundaries(self):
        """Test validation accepts limit at boundaries."""
        op = ListOrdersOperation()
        errors = op.validate({"limit": 1})
        assert len(errors) == 0

        errors = op.validate({"limit": 100})
        assert len(errors) == 0

    def test_execute_calls_api_with_defaults(self):
        """Test execute passes default values to API."""
        op = ListOrdersOperation()
        api = Mock()
        api.list_orders.return_value = {"orders": []}

        op.execute(api, {})

        api.list_orders.assert_called_once_with(limit=20, offset=0)

    def test_execute_calls_api_with_parameters(self):
        """Test execute passes provided parameters to API."""
        op = ListOrdersOperation()
        api = Mock()
        api.list_orders.return_value = {"orders": []}

        op.execute(api, {"limit": 50, "offset": 100})

        api.list_orders.assert_called_once_with(limit=50, offset=100)


class TestGetOrderOperation:
    """Test GetOrderOperation."""

    def test_validate_missing_order_id(self):
        """Test validation requires order_id."""
        op = GetOrderOperation()
        errors = op.validate({})
        assert len(errors) > 0
        assert any("order_id" in e for e in errors)

    def test_validate_invalid_order_id_not_integer(self):
        """Test validation rejects non-integer order_id."""
        op = GetOrderOperation()
        errors = op.validate({"order_id": "abc"})
        assert len(errors) > 0
        assert any("order_id" in e for e in errors)

    def test_validate_invalid_order_id_zero(self):
        """Test validation rejects order_id < 1."""
        op = GetOrderOperation()
        errors = op.validate({"order_id": 0})
        assert len(errors) > 0
        assert any("order_id" in e for e in errors)

    def test_validate_invalid_order_id_negative(self):
        """Test validation rejects negative order_id."""
        op = GetOrderOperation()
        errors = op.validate({"order_id": -1})
        assert len(errors) > 0
        assert any("order_id" in e for e in errors)

    def test_validate_valid_order_id(self):
        """Test validation accepts valid order_id."""
        op = GetOrderOperation()
        errors = op.validate({"order_id": 1})
        assert len(errors) == 0

    def test_execute_calls_api(self):
        """Test execute calls api.get_order()."""
        op = GetOrderOperation()
        api = Mock()
        api.get_order.return_value = {"order_id": 123, "status": "completed"}

        result = op.execute(api, {"order_id": 123})

        api.get_order.assert_called_once_with(123)
        assert result == {"order_id": 123, "status": "completed"}
