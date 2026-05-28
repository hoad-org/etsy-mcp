"""Tests for AES-256-GCM encryption."""

import pytest
from src.crypto import CryptoManager


class TestCryptoManager:
    """Test encryption and decryption."""

    def test_encrypt_decrypt(self):
        """Test basic encryption and decryption roundtrip."""
        plaintext = "secret message"
        password = "strong-password-123"

        encrypted = CryptoManager.encrypt(plaintext, password)
        decrypted = CryptoManager.decrypt(encrypted, password)

        assert decrypted == plaintext
        assert encrypted != plaintext  # Should be encrypted

    def test_different_passwords_fail(self):
        """Test that decryption with wrong password fails."""
        plaintext = "secret data"
        password1 = "correct"
        password2 = "wrong"

        encrypted = CryptoManager.encrypt(plaintext, password1)

        with pytest.raises(ValueError):
            CryptoManager.decrypt(encrypted, password2)

    def test_key_derivation(self):
        """Test PBKDF2 key derivation with same salt."""
        password = "test-password"

        key1, salt1 = CryptoManager.derive_key(password)
        key2, salt2 = CryptoManager.derive_key(password, salt1)

        # Same password and salt should produce same key
        assert key1 == key2
        assert salt1 == salt2
        assert len(key1) == 32  # 256 bits
        assert len(salt1) == 16  # 128 bits
