"""Immutable JSONL audit logging with HMAC-SHA256 integrity signing."""

import json
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    """Manage JSONL audit logs with HMAC signatures."""

    HMAC_SECRET = "audit-log-integrity"  # TODO: Move to secure key derivation

    def __init__(self, log_dir: str) -> None:
        """Initialize audit logger with log directory."""
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, action: str, details: dict[str, Any], redact: list[str] | None = None) -> None:
        """
        Log action to JSONL with HMAC signature.

        Args:
            action: Action name (e.g., "get_shop_info", "list_products")
            details: Details dictionary
            redact: List of keys to redact from logs (e.g., ["api_token", "password"])
        """
        redact = redact or []

        # Redact sensitive fields
        safe_details = self._redact(details, redact)

        # Create log entry
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": safe_details,
        }

        # Add HMAC signature
        entry_str = json.dumps(entry, sort_keys=True)
        signature = hmac.new(
            self.HMAC_SECRET.encode(),
            entry_str.encode(),
            hashlib.sha256,
        ).hexdigest()
        entry["_signature"] = signature

        # Append to today's log file
        log_file = self.log_dir / f"{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def verify_integrity(self, log_file: Path) -> bool:
        """
        Verify JSONL file integrity using HMAC signatures.

        Returns: True if all signatures are valid, False otherwise.
        """
        try:
            with open(log_file) as f:
                for line in f:
                    if not line.strip():
                        continue

                    entry = json.loads(line)
                    stored_signature = entry.pop("_signature", None)

                    if not stored_signature:
                        return False

                    entry_str = json.dumps(entry, sort_keys=True)
                    expected_signature = hmac.new(
                        self.HMAC_SECRET.encode(),
                        entry_str.encode(),
                        hashlib.sha256,
                    ).hexdigest()

                    if stored_signature != expected_signature:
                        return False

            return True

        except Exception as e:
            raise ValueError(f"Failed to verify audit log: {e}") from e

    @staticmethod
    def _redact(data: dict[str, Any], redact_keys: list[str]) -> dict[str, Any]:
        """Redact sensitive keys from dictionary."""
        safe_data = {}
        for key, value in data.items():
            if key.lower() in [k.lower() for k in redact_keys]:
                safe_data[key] = "[REDACTED]"
            elif isinstance(value, dict):
                safe_data[key] = AuditLogger._redact(value, redact_keys)
            else:
                safe_data[key] = value
        return safe_data
