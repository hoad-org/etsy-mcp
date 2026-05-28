"""Tests for configuration."""

import json
import pytest
from pathlib import Path
from src.config import Config


class TestConfigHierarchy:
    """Test configuration defaults."""

    def test_config_defaults(self):
        """Test that code defaults are set."""
        config = Config()

        assert config.read_rate_limit == 50
        assert config.write_rate_limit == 5
        assert config.request_timeout == 30
        assert config.tls_verify is True
        assert config.log_level == "INFO"

    def test_config_has_required_fields(self):
        """Test that all required fields exist."""
        config = Config()

        assert hasattr(config, "etsy_api_key")
        assert hasattr(config, "vault_password")
        assert hasattr(config, "audit_log_dir")

    def test_config_load_returns_config(self, monkeypatch):
        """Test that Config.load() returns a Config object."""
        # Set required environment variables
        monkeypatch.setenv("ETSY_API_KEY", "test-key-123")
        monkeypatch.setenv("ETSY_VAULT_PASSWORD", "test-vault-password")

        config = Config.load()
        assert isinstance(config, Config)
        assert config.read_rate_limit > 0
        assert config.etsy_api_key == "test-key-123"
        assert config.vault_password == "test-vault-password"

    def test_config_env_overrides_defaults(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("ETSY_API_KEY", "env-key")
        monkeypatch.setenv("ETSY_VAULT_PASSWORD", "env-password")
        monkeypatch.setenv("READ_RATE_LIMIT", "100")
        monkeypatch.setenv("TLS_VERIFY", "false")

        config = Config.load()
        assert config.etsy_api_key == "env-key"
        assert config.read_rate_limit == 100
        assert config.tls_verify is False

    def test_config_type_conversion_int(self, monkeypatch):
        """Test that integer env vars are converted correctly."""
        monkeypatch.setenv("ETSY_API_KEY", "test-key")
        monkeypatch.setenv("ETSY_VAULT_PASSWORD", "test-password")
        monkeypatch.setenv("READ_RATE_LIMIT", "25")
        monkeypatch.setenv("WRITE_RATE_LIMIT", "3")
        monkeypatch.setenv("REQUEST_TIMEOUT", "60")

        config = Config.load()
        assert isinstance(config.read_rate_limit, int)
        assert config.read_rate_limit == 25
        assert config.write_rate_limit == 3
        assert config.request_timeout == 60

    def test_config_type_conversion_bool(self, monkeypatch):
        """Test that boolean env vars are converted correctly."""
        monkeypatch.setenv("ETSY_API_KEY", "test-key")
        monkeypatch.setenv("ETSY_VAULT_PASSWORD", "test-password")
        monkeypatch.setenv("TLS_VERIFY", "true")

        config = Config.load()
        assert isinstance(config.tls_verify, bool)
        assert config.tls_verify is True

    def test_config_missing_required_field(self, monkeypatch):
        """Test that missing required fields raise ValueError."""
        # Only set API key, not vault password
        monkeypatch.setenv("ETSY_API_KEY", "test-key")
        monkeypatch.delenv("ETSY_VAULT_PASSWORD", raising=False)

        with pytest.raises(ValueError, match="ETSY_VAULT_PASSWORD not configured"):
            Config.load()

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "etsy_api_key" in config_dict
        assert "read_rate_limit" in config_dict
        assert "log_level" in config_dict

    def test_config_load_from_master_config(self, monkeypatch, tmp_path):
        """Test loading config from master config file."""
        # Create master config directory
        master_dir = tmp_path / ".etsy-mcp"
        master_dir.mkdir()
        master_config = master_dir / "config.json"

        # Write master config
        master_config.write_text(json.dumps({
            "etsy_api_key": "master-key",
            "etsy_shop_id": "shop-123",
            "log_level": "DEBUG"
        }))

        # Mock the home directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ETSY_VAULT_PASSWORD", "test-password")

        config = Config.load()
        assert config.etsy_api_key == "master-key"
        assert config.etsy_shop_id == "shop-123"
        assert config.log_level == "DEBUG"

    def test_config_load_from_repo_config(self, monkeypatch, tmp_path):
        """Test loading config from repo config file."""
        # Create repo config directory
        monkeypatch.chdir(tmp_path)
        repo_dir = tmp_path / ".etsy-mcp"
        repo_dir.mkdir()
        repo_config = repo_dir / "config.json"

        # Write repo config
        repo_config.write_text(json.dumps({
            "etsy_api_key": "repo-key",
            "log_level": "INFO"
        }))

        monkeypatch.setenv("ETSY_VAULT_PASSWORD", "test-password")

        config = Config.load()
        assert config.etsy_api_key == "repo-key"
        assert config.log_level == "INFO"

    def test_config_env_overrides_master_and_repo(self, monkeypatch, tmp_path):
        """Test that environment variables override master and repo config."""
        # Create both master and repo config
        master_dir = tmp_path / ".etsy-mcp"
        master_dir.mkdir()
        master_config = master_dir / "config.json"
        master_config.write_text(json.dumps({"log_level": "DEBUG"}))

        monkeypatch.chdir(tmp_path)
        repo_dir = tmp_path / ".etsy-mcp"
        repo_config = repo_dir / "config.json"
        repo_config.write_text(json.dumps({"log_level": "INFO"}))

        # Set environment variable
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("ETSY_API_KEY", "env-key")
        monkeypatch.setenv("ETSY_VAULT_PASSWORD", "test-password")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config.load()
        assert config.log_level == "WARNING"  # Environment wins

    def test_config_missing_api_key_raises_error(self, monkeypatch):
        """Test that missing API key raises ValueError."""
        monkeypatch.delenv("ETSY_API_KEY", raising=False)
        monkeypatch.setenv("ETSY_VAULT_PASSWORD", "test-password")

        with pytest.raises(ValueError, match="ETSY_API_KEY not configured"):
            Config.load()
