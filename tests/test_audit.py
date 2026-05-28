"""Tests for audit logging."""

import json
import pytest
from src.audit import AuditLogger


class TestAuditLogger:
    """Test audit logging."""

    def test_log_creation(self, tmp_path):
        """Test that logs are created."""
        logger = AuditLogger(str(tmp_path))
        logger.log("test_action", {"data": "value"})

        log_files = list(tmp_path.glob("*.jsonl"))
        assert len(log_files) == 1

    def test_log_has_required_fields(self, tmp_path):
        """Test that log entries have required fields."""
        logger = AuditLogger(str(tmp_path))
        logger.log("my_action", {"key": "value"})

        log_file = list(tmp_path.glob("*.jsonl"))[0]
        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert "timestamp" in entry
        assert "action" in entry
        assert "_signature" in entry
        assert entry["action"] == "my_action"

    def test_integrity_verification_passes_for_valid_logs(self, tmp_path):
        """Test that integrity verification passes for unmodified logs."""
        logger = AuditLogger(str(tmp_path))
        logger.log("action1", {"data": "value1"})

        log_file = list(tmp_path.glob("*.jsonl"))[0]
        is_valid = logger.verify_integrity(str(log_file))

        assert is_valid is True

    def test_redaction_hides_sensitive_data(self, tmp_path):
        """Test that sensitive data is redacted in logs."""
        logger = AuditLogger(str(tmp_path))
        logger.log("api_call", {"api_token": "secret123", "data": "public"}, redact=["api_token"])

        log_file = list(tmp_path.glob("*.jsonl"))[0]
        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["details"]["api_token"] == "[REDACTED]"
        assert entry["details"]["data"] == "public"

    def test_redaction_case_insensitive(self, tmp_path):
        """Test that redaction is case-insensitive."""
        logger = AuditLogger(str(tmp_path))
        logger.log("action", {"API_TOKEN": "secret", "password": "hidden"}, redact=["api_token", "PASSWORD"])

        log_file = list(tmp_path.glob("*.jsonl"))[0]
        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["details"]["API_TOKEN"] == "[REDACTED]"
        assert entry["details"]["password"] == "[REDACTED]"

    def test_integrity_verification_fails_for_modified_logs(self, tmp_path):
        """Test that integrity verification fails when logs are modified."""
        logger = AuditLogger(str(tmp_path))
        logger.log("action1", {"data": "value1"})

        log_file = list(tmp_path.glob("*.jsonl"))[0]

        # Modify the log file
        with open(log_file, "r") as f:
            content = f.read()

        entry = json.loads(content.strip())
        entry["details"]["data"] = "modified_value"

        with open(log_file, "w") as f:
            f.write(json.dumps(entry) + "\n")

        is_valid = logger.verify_integrity(str(log_file))
        assert is_valid is False

    def test_verify_integrity_raises_on_missing_signature(self, tmp_path):
        """Test that verify_integrity raises error when signature is missing."""
        logger = AuditLogger(str(tmp_path))
        log_file = tmp_path / "test.jsonl"

        # Write log entry without signature
        entry = {"timestamp": "2024-01-01T00:00:00", "action": "test"}
        with open(log_file, "w") as f:
            f.write(json.dumps(entry) + "\n")

        is_valid = logger.verify_integrity(str(log_file))
        assert is_valid is False

    def test_verify_integrity_raises_on_corrupt_file(self, tmp_path):
        """Test that verify_integrity raises ValueError on corrupt file."""
        logger = AuditLogger(str(tmp_path))
        log_file = tmp_path / "corrupt.jsonl"

        # Write invalid JSON
        with open(log_file, "w") as f:
            f.write("not valid json\n")

        with pytest.raises(ValueError, match="Failed to verify audit log"):
            logger.verify_integrity(str(log_file))
