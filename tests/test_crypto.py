"""Tests for crypto module."""

import pytest
from src.crypto import CryptoManager


class TestCryptoManager:
    """Test AES-256-GCM encryption and PBKDF2 key derivation."""

    def test_encrypt_decrypt(self) -> None:
        """Test encrypt/decrypt roundtrip."""
        password = "test-password-123"
        plaintext = "secret-api-key"

        encrypted = CryptoManager.encrypt(plaintext, password)
        decrypted = CryptoManager.decrypt(encrypted, password)

        assert decrypted == plaintext

    def test_different_passwords_fail(self) -> None:
        """Test that different passwords fail decryption."""
        plaintext = "secret-api-key"
        encrypted = CryptoManager.encrypt(plaintext, "password1")

        with pytest.raises(ValueError, match="Decryption failed"):
            CryptoManager.decrypt(encrypted, "password2")

    def test_key_derivation(self) -> None:
        """Test PBKDF2 key derivation."""
        password = "test-password"

        key1, salt1 = CryptoManager.derive_key(password)
        key2, salt2 = CryptoManager.derive_key(password, salt1)

        assert key1 == key2
        assert salt1 == salt2
        assert len(key1) == 32  # 256 bits
        assert len(salt1) == 16  # 128 bits
