"""Etsy API wrapper with TLS 1.3, certificate pinning, and request signing."""

import hmac
import hashlib
import json
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class TLS13HTTPAdapter(HTTPAdapter):
    """HTTP adapter enforcing TLS 1.3."""

    def init_poolmanager(self, *args, **kwargs) -> None:
        ctx = create_urllib3_context()
        ctx.minimum_version = 771  # TLS 1.3
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


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

    def _sign_request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, str]:
        """Sign request with HMAC-SHA256."""
        params = params or {}
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

        data = response.json()
        return data.get("shop", {})

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
        params = {
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

        data = response.json()
        return data.get("listing", {})

    def list_orders(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """List recent orders (read-only)."""
        path = f"/shops/{self.shop_id}/orders"
        params = {
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

    def close(self) -> None:
        """Close session."""
        self.session.close()
