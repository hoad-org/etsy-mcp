"""Tests for config module."""

import os
import json
import tempfile
from pathlib import Path
import pytest
from src.config import Config


class TestConfigHierarchy:
    """Test 4-level configuration hierarchy."""

    def test_code_defaults(self) -> None:
        """Test code defaults are used."""
        # Override env vars
        os.environ.pop("ETSY_API_KEY", None)
        os.environ.pop("ETSY_VAULT_PASSWORD", None)

        # Should fail because required vars are missing
        with pytest.raises(ValueError, match="not configured"):
            Config.load()

    def test_env_override(self) -> None:
        """Test environment variables override everything."""
        os.environ["ETSY_API_KEY"] = "env-key"
        os.environ["ETSY_VAULT_PASSWORD"] = "env-password"

        config = Config.load()

        assert config.etsy_api_key == "env-key"
        assert config.vault_password == "env-password"

        # Cleanup
        os.environ.pop("ETSY_API_KEY", None)
        os.environ.pop("ETSY_VAULT_PASSWORD", None)

    def test_required_fields(self) -> None:
        """Test required fields must be set."""
        os.environ.pop("ETSY_API_KEY", None)
        os.environ.pop("ETSY_VAULT_PASSWORD", None)

        with pytest.raises(ValueError, match="ETSY_API_KEY"):
            Config.load()

    def test_type_conversions(self) -> None:
        """Test environment variable type conversions."""
        os.environ["ETSY_API_KEY"] = "test-key"
        os.environ["ETSY_VAULT_PASSWORD"] = "test-password"
        os.environ["READ_RATE_LIMIT"] = "100"
        os.environ["TLS_VERIFY"] = "false"

        config = Config.load()

        assert config.read_rate_limit == 100
        assert config.tls_verify is False

        # Cleanup
        os.environ.pop("ETSY_API_KEY", None)
        os.environ.pop("ETSY_VAULT_PASSWORD", None)
        os.environ.pop("READ_RATE_LIMIT", None)
        os.environ.pop("TLS_VERIFY", None)
