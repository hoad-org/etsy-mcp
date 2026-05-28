"""Tests for audit logging module."""

import tempfile
from pathlib import Path
import json
import pytest
from src.audit import AuditLogger


class TestAuditLogger:
    """Test JSONL audit logging with HMAC signatures."""

    def test_log_creation(self) -> None:
        """Test that logs are created and signed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logger.log("test_action", {"key": "value"})

            # Check log file exists
            log_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(log_files) == 1

            # Check content
            with open(log_files[0]) as f:
                entry = json.loads(f.read())
                assert entry["action"] == "test_action"
                assert entry["details"]["key"] == "value"
                assert "_signature" in entry

    def test_redaction(self) -> None:
        """Test that sensitive fields are redacted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logger.log(
                "test_action",
                {"api_token": "secret-token", "public_info": "ok"},
                redact=["api_token"],
            )

            log_files = list(Path(tmpdir).glob("*.jsonl"))
            with open(log_files[0]) as f:
                entry = json.loads(f.read())
                assert entry["details"]["api_token"] == "[REDACTED]"
                assert entry["details"]["public_info"] == "ok"

    def test_integrity_verification(self) -> None:
        """Test that HMAC signatures verify integrity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logger.log("test_action", {"key": "value"})

            log_file = list(Path(tmpdir).glob("*.jsonl"))[0]
            assert logger.verify_integrity(log_file)
