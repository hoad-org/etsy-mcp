"""P1 (Read-Only) Operations — Complete Product Management."""

from typing import Any

from src.operations import BaseOperationDef, Operation, ParameterSchema
from src.operation_registry import REGISTRY


class GetShopInfoOperation(BaseOperationDef):
    """Get shop information (read-only)."""

    name = "get_shop_info"
    operation_type = Operation.READ
    description = "Get shop information (rates, shipping, policies)"
    rate_limit_type = "read"
    parameters = {}
    required_params = []

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        return []  # No parameters

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.get_shop()


class ListListingsOperation(BaseOperationDef):
    """List listings with filtering and pagination (read-only)."""

    name = "list_listings"
    operation_type = Operation.READ
    description = "List products from shop with filters and pagination"
    rate_limit_type = "read"
    parameters = {
        "status": ParameterSchema(
            "string",
            description="Product status (active, draft, sold_out)",
            default="active",
            enum_values=["active", "draft", "sold_out"],
        ),
        "limit": ParameterSchema(
            "integer",
            description="Max results (1-100)",
            default=20,
            min_value=1,
            max_value=100,
        ),
        "offset": ParameterSchema(
            "integer",
            description="Pagination offset",
            default=0,
            min_value=0,
        ),
        "sort_by": ParameterSchema(
            "string",
            description="Sort field (created, updated, price)",
            default="created",
            enum_values=["created", "updated", "price"],
        ),
    }
    required_params = []

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors = super().validate(arguments)

        # Additional validation for parameter combinations
        if "limit" in arguments and not (1 <= arguments["limit"] <= 100):
            errors.append("limit must be between 1 and 100")
        if "offset" in arguments and arguments["offset"] < 0:
            errors.append("offset must be >= 0")

        return errors

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.list_listings(
            status=arguments.get("status", "active"),
            limit=arguments.get("limit", 20),
            offset=arguments.get("offset", 0),
            sort_by=arguments.get("sort_by", "created"),
        )


class GetListingOperation(BaseOperationDef):
    """Get product details (read-only)."""

    name = "get_listing"
    operation_type = Operation.READ
    description = "Get product details (price, inventory, images, tags)"
    rate_limit_type = "read"
    parameters = {
        "listing_id": ParameterSchema(
            "integer",
            description="Product listing ID",
            required=True,
            min_value=1,
        ),
    }
    required_params = ["listing_id"]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors = super().validate(arguments)

        if "listing_id" in arguments:
            listing_id = arguments["listing_id"]
            if not isinstance(listing_id, int) or listing_id < 1:
                errors.append("listing_id must be a positive integer")

        return errors

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.get_listing(arguments["listing_id"])


class GetListingInventoryOperation(BaseOperationDef):
    """Get listing inventory levels by SKU (read-only)."""

    name = "get_listing_inventory"
    operation_type = Operation.READ
    description = "Check current stock levels by SKU/variation"
    rate_limit_type = "read"
    parameters = {
        "listing_id": ParameterSchema(
            "integer",
            description="Product listing ID",
            required=True,
            min_value=1,
        ),
    }
    required_params = ["listing_id"]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors = super().validate(arguments)

        if "listing_id" in arguments:
            listing_id = arguments["listing_id"]
            if not isinstance(listing_id, int) or listing_id < 1:
                errors.append("listing_id must be a positive integer")

        return errors

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.get_listing_inventory(arguments["listing_id"])


class ListOrdersOperation(BaseOperationDef):
    """List recent orders (read-only)."""

    name = "list_orders"
    operation_type = Operation.READ
    description = "List recent orders with status and customer details"
    rate_limit_type = "read"
    parameters = {
        "limit": ParameterSchema(
            "integer",
            description="Max results (1-100)",
            default=20,
            min_value=1,
            max_value=100,
        ),
        "offset": ParameterSchema(
            "integer",
            description="Pagination offset",
            default=0,
            min_value=0,
        ),
    }
    required_params = []

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors = super().validate(arguments)

        if "limit" in arguments and not (1 <= arguments["limit"] <= 100):
            errors.append("limit must be between 1 and 100")
        if "offset" in arguments and arguments["offset"] < 0:
            errors.append("offset must be >= 0")

        return errors

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.list_orders(
            limit=arguments.get("limit", 20),
            offset=arguments.get("offset", 0),
        )


class GetOrderOperation(BaseOperationDef):
    """Get order details (read-only)."""

    name = "get_order"
    operation_type = Operation.READ
    description = "Fetch single order (items, shipping, buyer info)"
    rate_limit_type = "read"
    parameters = {
        "order_id": ParameterSchema(
            "integer",
            description="Order ID",
            required=True,
            min_value=1,
        ),
    }
    required_params = ["order_id"]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors = super().validate(arguments)

        if "order_id" in arguments:
            order_id = arguments["order_id"]
            if not isinstance(order_id, int) or order_id < 1:
                errors.append("order_id must be a positive integer")

        return errors

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.get_order(arguments["order_id"])


# Register all P1 operations
REGISTRY.register(GetShopInfoOperation())
REGISTRY.register(ListListingsOperation())
REGISTRY.register(GetListingOperation())
REGISTRY.register(GetListingInventoryOperation())
REGISTRY.register(ListOrdersOperation())
REGISTRY.register(GetOrderOperation())
