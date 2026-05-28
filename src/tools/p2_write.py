"""P2 (Write, Requires Approval) Operations — Product Management Updates."""

from typing import Any

from src.operations import BaseOperationDef, Operation, ParameterSchema
from src.operation_registry import REGISTRY


class UpdateListingOperation(BaseOperationDef):
    """Update listing fields (requires approval)."""

    name = "update_listing"
    operation_type = Operation.WRITE
    description = "Modify listing fields (title, description, price, tags, shipping)"
    rate_limit_type = "write"
    parameters = {
        "listing_id": ParameterSchema(
            "integer",
            description="Product listing ID",
            required=True,
            min_value=1,
        ),
        "updates": ParameterSchema(
            "object",
            description="Fields to update (title, description, price, tags, shipping, materials)",
            required=True,
        ),
    }
    required_params = ["listing_id", "updates"]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors = super().validate(arguments)

        if "listing_id" in arguments:
            listing_id = arguments["listing_id"]
            if not isinstance(listing_id, int) or listing_id < 1:
                errors.append("listing_id must be a positive integer")

        if "updates" in arguments:
            updates = arguments["updates"]
            if not isinstance(updates, dict):
                errors.append("updates must be a dictionary")
            elif not updates:
                errors.append("updates cannot be empty")

        return errors

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.update_listing(
            arguments["listing_id"],
            arguments["updates"],
        )


class UpdateListingInventoryOperation(BaseOperationDef):
    """Update listing inventory levels (requires approval)."""

    name = "update_listing_inventory"
    operation_type = Operation.WRITE
    description = "Update stock levels by SKU/variation"
    rate_limit_type = "write"
    parameters = {
        "listing_id": ParameterSchema(
            "integer",
            description="Product listing ID",
            required=True,
            min_value=1,
        ),
        "inventory_updates": ParameterSchema(
            "array",
            description="List of {sku, quantity} dicts to update",
            required=True,
        ),
    }
    required_params = ["listing_id", "inventory_updates"]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors = super().validate(arguments)

        if "listing_id" in arguments:
            listing_id = arguments["listing_id"]
            if not isinstance(listing_id, int) or listing_id < 1:
                errors.append("listing_id must be a positive integer")

        if "inventory_updates" in arguments:
            inventory_updates = arguments["inventory_updates"]
            if not isinstance(inventory_updates, list):
                errors.append("inventory_updates must be a list")
            elif not inventory_updates:
                errors.append("inventory_updates cannot be empty")
            else:
                for i, update in enumerate(inventory_updates):
                    if not isinstance(update, dict):
                        errors.append(f"inventory_updates[{i}] must be a dict")
                    elif "sku" not in update or "quantity" not in update:
                        errors.append(f"inventory_updates[{i}] must have 'sku' and 'quantity'")

        return errors

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.update_listing_inventory(
            arguments["listing_id"],
            arguments["inventory_updates"],
        )


class PublishListingOperation(BaseOperationDef):
    """Publish (activate) a draft listing (requires approval)."""

    name = "publish_listing"
    operation_type = Operation.WRITE
    description = "Activate draft listing to shop"
    rate_limit_type = "write"
    parameters = {
        "listing_id": ParameterSchema(
            "integer",
            description="Product listing ID (must be in draft state)",
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
        return api.publish_listing(arguments["listing_id"])


class DeactivateListingOperation(BaseOperationDef):
    """Deactivate (disable) a listing (requires approval)."""

    name = "deactivate_listing"
    operation_type = Operation.WRITE
    description = "Temporarily disable listing from shop"
    rate_limit_type = "write"
    parameters = {
        "listing_id": ParameterSchema(
            "integer",
            description="Product listing ID (must be active)",
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
        return api.deactivate_listing(arguments["listing_id"])


class UpdateShopInfoOperation(BaseOperationDef):
    """Update shop information (requires approval)."""

    name = "update_shop_info"
    operation_type = Operation.WRITE
    description = "Update shop policies, announcements, and vacation mode"
    rate_limit_type = "write"
    parameters = {
        "updates": ParameterSchema(
            "object",
            description="Fields to update (announcement, vacation_mode, return_policy)",
            required=True,
        ),
    }
    required_params = ["updates"]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors = super().validate(arguments)

        if "updates" in arguments:
            updates = arguments["updates"]
            if not isinstance(updates, dict):
                errors.append("updates must be a dictionary")
            elif not updates:
                errors.append("updates cannot be empty")

        return errors

    def execute(self, api: Any, arguments: dict[str, Any]) -> Any:
        return api.update_shop_info(arguments["updates"])


# Register all P2 operations
REGISTRY.register(UpdateListingOperation())
REGISTRY.register(UpdateListingInventoryOperation())
REGISTRY.register(PublishListingOperation())
REGISTRY.register(DeactivateListingOperation())
REGISTRY.register(UpdateShopInfoOperation())
