"""Mock Etsy API client for testing without hitting real API."""

from typing import Any


class MockEtsyAPI:
    """Mock Etsy API that returns realistic test data for all P1 operations."""

    def __init__(self, shop_id: str = "12345678") -> None:
        """Initialize mock API with shop ID."""
        self.shop_id = shop_id

    def get_shop(self) -> dict[str, Any]:
        """Get shop information (read-only)."""
        return {
            "shop_id": int(self.shop_id),
            "shop_name": "Vintage Horror Collectibles",
            "user_id": 987654321,
            "icon_url_fullxfull": "https://example.com/shop_icon.jpg",
            "is_vacation": False,
            "vacation_message": "",
            "sale_message": "Spring Sale: 20% off vintage posters!",
            "shop_announcement": "New inventory every week. Follow for updates!",
            "created_tsz": 1577836800,
            "updated_tsz": 1609459200,
            "policy_welcome": "Welcome to our shop!",
            "policy_payment": "We accept all major payment methods",
            "policy_shipping": "Ships within 5 business days. Free shipping on orders over £30.",
            "policy_refunds": "30-day money-back guarantee",
            "policy_additional": "All items inspected for quality before shipping",
            "policy_seller_info": "Family-run vintage collectibles specialist since 2018",
            "policy_update_tsz": 1609459200,
            "listing_active_count": 147,
            "num_favorers": 523,
            "include_dispute_form_link": False,
            "is_refusing_payments": False,
            "has_unencrypted_conversations": False,
            "accepts_gift_cards": True,
            "shop_return_policy_set_after_sale": False,
            "country_code": "GB",
            "currency_code": "GBP",
        }

    def list_listings(
        self,
        status: str = "active",
        limit: int = 20,
        offset: int = 0,
        sort: str = "date",
        tag: str | None = None,
    ) -> dict[str, Any]:
        """List listings with filtering and pagination (read-only)."""
        total_listings = 147

        # Filter by status if not "all"
        if status != "all":
            # Mock: filter would reduce count
            total_filtered = 140 if status == "active" else 7
        else:
            total_filtered = total_listings

        results = []
        for i in range(offset, min(offset + limit, total_filtered)):
            listing_id = 100000 + i
            results.append({
                "listing_id": listing_id,
                "user_id": 987654321,
                "shop_id": int(self.shop_id),
                "title": f"Vintage Horror Poster {i+1}",
                "description": "Authentic vintage movie poster from the 1970s-80s. Excellent condition. Original frame-ready.",
                "price": {
                    "amount": 1999 + (i % 20) * 100,
                    "divisor": 100,
                    "currency_code": "GBP",
                },
                "creation_tsz": 1609459200 + (i * 86400),
                "last_modified_tsz": 1609459200 + (i * 86400),
                "state": status if status != "all" else "active",
                "quantity": max(0, 5 - (i % 7)),
                "category_id": 69150049,
                "tags": ["vintage", "horror", "poster", "collectible"],
                "materials": ["paper", "ink"],
                "url": f"https://www.etsy.com/listing/{listing_id}/vintage-horror-poster",
            })

        return {
            "count": len(results),
            "results": results,
            "pagination": {
                "effective_limit": limit,
                "effective_offset": offset,
                "next_offset": offset + limit if offset + limit < total_filtered else None,
                "total": total_filtered,
            },
        }

    def get_listing(self, listing_id: int) -> dict[str, Any]:
        """Get single listing details (read-only)."""
        if listing_id < 100000 or listing_id >= 100147:
            raise Exception(f"404 Listing {listing_id} not found")

        return {
            "listing_id": listing_id,
            "user_id": 987654321,
            "shop_id": int(self.shop_id),
            "title": "Vintage Horror Movie Poster - The Exorcist (1973)",
            "description": "Authentic vintage original release poster. Professionally framed, ready to display. Minor age-appropriate wear consistent with 1973 production.",
            "price": {"amount": 2499, "divisor": 100, "currency_code": "GBP"},
            "quantity": 1,
            "state": "active",
            "creation_tsz": 1609459200,
            "last_modified_tsz": 1609459200,
            "category_id": 69150049,
            "tags": ["vintage", "horror", "exorcist", "1973", "collectible"],
            "materials": ["paper", "ink", "wood frame"],
            "images": [
                {
                    "listing_image_id": 900001,
                    "hex_code": None,
                    "is_primary": True,
                    "ranking": 0,
                    "url_75x75": "https://example.com/img_75.jpg",
                    "url_170x135": "https://example.com/img_170.jpg",
                    "url_570xN": "https://example.com/img_570.jpg",
                }
            ],
            "has_variations": False,
            "shipping": {
                "min_processing_days": 1,
                "max_processing_days": 5,
                "min_delivery_days": 5,
                "max_delivery_days": 10,
            },
            "url": f"https://www.etsy.com/listing/{listing_id}/vintage-horror-poster",
        }

    def get_listing_inventory(self, listing_id: int) -> dict[str, Any]:
        """Get listing inventory by SKU (read-only)."""
        if listing_id < 100000 or listing_id >= 100147:
            raise Exception(f"404 Listing {listing_id} not found")

        return {
            "listing_id": listing_id,
            "products": [
                {
                    "product_id": 500001,
                    "sku": "VHP-EXORCIST-1973",
                    "property_values": [],
                    "offerings": [
                        {
                            "offering_id": 600001,
                            "quantity": 3,
                            "is_enabled": True,
                            "price": {"amount": 2499, "divisor": 100, "currency_code": "GBP"},
                        }
                    ],
                }
            ],
        }

    def list_orders(
        self,
        status: str = "all",
        limit: int = 20,
        offset: int = 0,
        earliest: int | None = None,
        latest: int | None = None,
    ) -> dict[str, Any]:
        """List orders with filtering and pagination (read-only)."""
        total_orders = 523

        results = []
        for i in range(offset, min(offset + limit, total_orders)):
            order_id = 500000 + i
            results.append({
                "order_id": order_id,
                "receipt_id": order_id + 1000000,
                "seller_user_id": int(self.shop_id),
                "buyer_user_id": 111111111 + i,
                "status": "completed" if i % 5 != 0 else "shipped",
                "price": {"amount": 2999 + (i % 10) * 100, "divisor": 100, "currency_code": "GBP"},
                "creation_tsz": 1609459200 - (i * 86400),
                "last_modified_tsz": 1609459200 - (i * 86400),
                "is_paid": True,
                "is_shipped": i % 3 != 0,
                "num_items": 1,
            })

        return {
            "count": len(results),
            "results": results,
            "pagination": {
                "effective_limit": limit,
                "effective_offset": offset,
                "next_offset": offset + limit if offset + limit < total_orders else None,
                "total": total_orders,
            },
        }

    def get_order(self, order_id: int) -> dict[str, Any]:
        """Get single order details (read-only)."""
        if order_id < 500000 or order_id >= 500523:
            raise Exception(f"404 Order {order_id} not found")

        return {
            "order_id": order_id,
            "receipt_id": order_id + 1000000,
            "seller_user_id": int(self.shop_id),
            "buyer_user_id": 111111111,
            "buyer_email": "collector@example.com",
            "buyer_name": "John Collector",
            "status": "completed",
            "price": {"amount": 2999, "divisor": 100, "currency_code": "GBP"},
            "shipping_price": {"amount": 0, "divisor": 100, "currency_code": "GBP"},
            "tax_price": {"amount": 600, "divisor": 100, "currency_code": "GBP"},
            "creation_tsz": 1609459200,
            "last_modified_tsz": 1609459200,
            "is_paid": True,
            "is_shipped": True,
            "is_delivered": True,
            "num_items": 2,
            "shipments": [
                {
                    "shipment_id": 700001,
                    "carrier_name": "Royal Mail",
                    "tracking_code": "RX123456789GB",
                    "creation_tsz": 1609545600,
                    "expected_delivery_date": 1609718400,
                }
            ],
            "transactions": [
                {
                    "transaction_id": 800001,
                    "listing_id": 100000,
                    "quantity": 1,
                    "price": {"amount": 1499, "divisor": 100, "currency_code": "GBP"},
                    "title": "Vintage Horror Poster 1",
                    "receipt_id": order_id + 1000000,
                    "creation_tsz": 1609459200,
                },
                {
                    "transaction_id": 800002,
                    "listing_id": 100001,
                    "quantity": 1,
                    "price": {"amount": 1500, "divisor": 100, "currency_code": "GBP"},
                    "title": "Vintage Horror Poster 2",
                    "receipt_id": order_id + 1000000,
                    "creation_tsz": 1609459200,
                },
            ],
            "buyer_shipping_address": {
                "name": "John Collector",
                "first_line": "123 Main Street",
                "second_line": "",
                "city": "London",
                "state": "England",
                "zip": "SW1A 1AA",
                "country_iso": "GB",
                "country_name": "United Kingdom",
            },
        }
