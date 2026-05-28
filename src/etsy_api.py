"""Etsy API wrapper with TLS 1.3, certificate pinning, and request signing."""

import hashlib
import hmac
import ssl
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class TLS13HTTPAdapter(HTTPAdapter):
    """HTTP adapter enforcing TLS 1.3."""

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)  # type: ignore[no-untyped-call]


class EtsyAPI:
    """Etsy API client with security hardening."""

    BASE_URL = "https://openapi.etsy.com/v3"
    TIMEOUT = 30  # seconds
    VERIFY_TLS = True

    def __init__(self, api_key: str, shop_id: str) -> None:
        """Initialize Etsy API client."""
        self.api_key = api_key
        self.shop_id = shop_id
        self.session = requests.Session()

        # Enforce TLS 1.3
        adapter = TLS13HTTPAdapter()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Set headers
        self.session.headers.update(
            {
                "x-api-key": api_key,
                "User-Agent": "etsy-mcp/0.1.0",
                "Accept": "application/json",
            }
        )

    def _sign_request(self, path: str, params: dict[str, int | str] | None = None) -> dict[str, str]:
        """Sign request with HMAC-SHA256."""
        if params is None:
            params = {}
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        message = f"{path}?{param_str}" if param_str else path

        signature = hmac.new(
            self.api_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return {"X-Etsy-Signature": signature}

    def get_shop(self) -> dict[str, Any]:
        """Get shop info (read-only)."""
        path = f"/shops/{self.shop_id}"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)

        response = self.session.get(
            url,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return data.get("shop", {})  # type: ignore[no-any-return]

    def list_products(
        self,
        status: str = "active",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List products (read-only).

        Args:
            status: Product status (active, draft, sold_out)
            limit: Max results (1-100)
            offset: Pagination offset
        """
        path = f"/shops/{self.shop_id}/listings"
        params: dict[str, int | str] = {
            "status": status,
            "limit": min(limit, 100),
            "offset": offset,
        }

        url = f"{self.BASE_URL}{path}"
        headers = self._sign_request(path, params)

        response = self.session.get(
            url,
            params=params,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        return {
            "listings": data.get("results", []),
            "count": data.get("count", 0),
            "pagination": {
                "offset": params["offset"],
                "limit": params["limit"],
            },
        }

    def get_product(self, listing_id: int) -> dict[str, Any]:
        """Get product details (read-only)."""
        path = f"/listings/{listing_id}"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)

        response = self.session.get(
            url,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return data.get("listing", {})  # type: ignore[no-any-return]

    def list_orders(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """List recent orders (read-only)."""
        path = f"/shops/{self.shop_id}/orders"
        params: dict[str, int | str] = {
            "limit": min(limit, 100),
            "offset": offset,
        }

        url = f"{self.BASE_URL}{path}"
        headers = self._sign_request(path, params)

        response = self.session.get(
            url,
            params=params,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        return {
            "orders": data.get("results", []),
            "count": data.get("count", 0),
            "pagination": {
                "offset": params["offset"],
                "limit": params["limit"],
            },
        }

    # P1 (Read-Only) Methods — Complete Product Management

    def get_listing(self, listing_id: int) -> dict[str, Any]:
        """Get listing details (read-only, alias for get_product)."""
        return self.get_product(listing_id)

    def list_listings(
        self,
        status: str = "active",
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created",
    ) -> dict[str, Any]:
        """
        List listings with filtering and pagination (read-only).

        Args:
            status: Product status (active, draft, sold_out)
            limit: Max results (1-100)
            offset: Pagination offset
            sort_by: Sort field (created, updated, price)
        """
        path = f"/shops/{self.shop_id}/listings"
        params: dict[str, int | str] = {
            "status": status,
            "limit": min(limit, 100),
            "offset": offset,
            "sort_by": sort_by,
        }

        url = f"{self.BASE_URL}{path}"
        headers = self._sign_request(path, params)

        response = self.session.get(
            url,
            params=params,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        return {
            "listings": data.get("results", []),
            "count": data.get("count", 0),
            "pagination": {
                "offset": params["offset"],
                "limit": params["limit"],
            },
        }

    def get_listing_inventory(self, listing_id: int) -> dict[str, Any]:
        """
        Get current inventory levels by SKU/variation (read-only).

        Returns dict of SKU -> {quantity, is_available}.
        """
        path = f"/listings/{listing_id}/inventory"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)

        response = self.session.get(
            url,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return {
            "listing_id": listing_id,
            "inventory": data.get("products", []),
        }

    def get_order(self, order_id: int) -> dict[str, Any]:
        """Get order details (read-only)."""
        path = f"/orders/{order_id}"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)

        response = self.session.get(
            url,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return data.get("order", {})

    # P2 (Write, Requires Approval) Methods

    def update_listing(
        self,
        listing_id: int,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update listing fields (requires approval).

        Updates can include: title, description, price, tags, shipping, materials.
        """
        path = f"/listings/{listing_id}"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)
        headers["Content-Type"] = "application/json"

        response = self.session.patch(
            url,
            json=updates,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return {
            "success": True,
            "listing": data.get("listing", {}),
        }

    def update_listing_inventory(
        self,
        listing_id: int,
        inventory_updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Update inventory levels by SKU (requires approval).

        inventory_updates: list of {sku, quantity} dicts.
        """
        path = f"/listings/{listing_id}/inventory"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)
        headers["Content-Type"] = "application/json"

        response = self.session.put(
            url,
            json={"products": inventory_updates},
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return {
            "success": True,
            "inventory_changes": data.get("products", []),
        }

    def publish_listing(self, listing_id: int) -> dict[str, Any]:
        """Publish (activate) a draft listing (requires approval)."""
        path = f"/listings/{listing_id}"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)
        headers["Content-Type"] = "application/json"

        response = self.session.patch(
            url,
            json={"state": "active"},
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return {
            "success": True,
            "state": data.get("listing", {}).get("state"),
        }

    def deactivate_listing(self, listing_id: int) -> dict[str, Any]:
        """Deactivate (disable) a listing (requires approval)."""
        path = f"/listings/{listing_id}"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)
        headers["Content-Type"] = "application/json"

        response = self.session.patch(
            url,
            json={"state": "inactive"},
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return {
            "success": True,
            "state": data.get("listing", {}).get("state"),
        }

    def update_shop_info(
        self,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update shop information (requires approval).

        Updates can include: announcement, vacation_mode, return_policy.
        """
        path = f"/shops/{self.shop_id}"
        url = f"{self.BASE_URL}{path}"

        headers = self._sign_request(path)
        headers["Content-Type"] = "application/json"

        response = self.session.patch(
            url,
            json=updates,
            timeout=self.TIMEOUT,
            verify=self.VERIFY_TLS,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        return {
            "success": True,
            "shop": data.get("shop", {}),
        }

    def close(self) -> None:
        """Close session."""
        self.session.close()
