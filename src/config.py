"""4-level configuration hierarchy: code defaults -> master -> repo -> env."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Config:
    """Etsy MCP configuration."""

    # API
    etsy_api_key: str = ""
    etsy_shop_id: str = ""

    # Encryption
    vault_password: str = ""

    # Logging
    log_level: str = "INFO"
    audit_log_dir: str = "~/.etsy-mcp/audit/"

    # Rate limiting
    read_rate_limit: int = 50  # reads per minute
    write_rate_limit: int = 5  # writes per minute
    dangerous_rate_limit: int = 1  # dangerous ops per 5 minutes

    # TLS
    tls_verify: bool = True
    tls_min_version: str = "TLSv1_3"

    # Timeouts
    request_timeout: int = 30  # seconds
    circuit_breaker_threshold: int = 5
    circuit_breaker_window: int = 60  # seconds

    @staticmethod
    def load() -> "Config":
        """Load config from 4-level hierarchy."""
        config = Config()

        # Level 1: Code defaults (already set)

        # Level 2: Master config (~/.etsy-mcp/config.json)
        master_config_path = Path.home() / ".etsy-mcp" / "config.json"
        if master_config_path.exists():
            with open(master_config_path) as f:
                master_data = json.load(f)
                for key, value in master_data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

        # Level 3: Repo config (./.etsy-mcp/config.json)
        repo_config_path = Path(".") / ".etsy-mcp" / "config.json"
        if repo_config_path.exists():
            with open(repo_config_path) as f:
                repo_data = json.load(f)
                for key, value in repo_data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

        # Level 4: Environment variables (highest priority)
        env_mapping = {
            "ETSY_API_KEY": "etsy_api_key",
            "ETSY_SHOP_ID": "etsy_shop_id",
            "ETSY_VAULT_PASSWORD": "vault_password",
            "LOG_LEVEL": "log_level",
            "AUDIT_LOG_DIR": "audit_log_dir",
            "READ_RATE_LIMIT": "read_rate_limit",
            "WRITE_RATE_LIMIT": "write_rate_limit",
            "DANGEROUS_RATE_LIMIT": "dangerous_rate_limit",
            "TLS_VERIFY": "tls_verify",
            "REQUEST_TIMEOUT": "request_timeout",
        }

        for env_var, config_attr in env_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # Type conversion
                if config_attr in ["tls_verify"]:
                    value = value.lower() in ("true", "1", "yes")
                elif config_attr in [
                    "read_rate_limit",
                    "write_rate_limit",
                    "dangerous_rate_limit",
                    "request_timeout",
                ]:
                    value = int(value)
                setattr(config, config_attr, value)

        # Validate
        if not config.etsy_api_key:
            raise ValueError("ETSY_API_KEY not configured")
        if not config.vault_password:
            raise ValueError("ETSY_VAULT_PASSWORD not configured")

        return config

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
