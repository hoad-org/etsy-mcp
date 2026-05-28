"""Etsy MCP tools (implemented via operation registry)."""

# Import operations to register them in REGISTRY
from src.tools.p1_read import (  # noqa: F401
    GetListingInventoryOperation,
    GetListingOperation,
    GetOrderOperation,
    GetShopInfoOperation,
    ListListingsOperation,
    ListOrdersOperation,
)
from src.tools.p2_write import (  # noqa: F401
    DeactivateListingOperation,
    PublishListingOperation,
    UpdateListingInventoryOperation,
    UpdateListingOperation,
    UpdateShopInfoOperation,
)
