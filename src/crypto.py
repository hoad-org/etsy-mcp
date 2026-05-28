"""AES-256-GCM encryption with PBKDF2 key derivation (NIST-compliant)."""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class CryptoManager:
    """Manage AES-256-GCM encryption with PBKDF2 key derivation."""

    ALGORITHM = "AES-256-GCM"
    KEY_SIZE = 32  # 256 bits
    ITERATIONS = 600_000  # NIST recommendation
    SALT_SIZE = 16  # 128 bits

    @staticmethod
    def derive_key(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
        """
        Derive 256-bit key from password using PBKDF2-SHA256.

        Returns: (key, salt)
        """
        if salt is None:
            salt = os.urandom(CryptoManager.SALT_SIZE)

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=CryptoManager.KEY_SIZE,
            salt=salt,
            iterations=CryptoManager.ITERATIONS,
            backend=default_backend(),
        )
        key = kdf.derive(password.encode())
        return key, salt

    @staticmethod
    def encrypt(plaintext: str, password: str) -> str:
        """
        Encrypt plaintext with AES-256-GCM.

        Returns base64-encoded: salt + nonce + ciphertext + tag
        """
        key, salt = CryptoManager.derive_key(password)
        nonce = os.urandom(12)  # 96-bit nonce (recommended for GCM)
        cipher = AESGCM(key)

        ciphertext = cipher.encrypt(nonce, plaintext.encode(), None)

        # Concatenate: salt + nonce + ciphertext (includes auth tag)
        encrypted_data = salt + nonce + ciphertext
        return base64.b64encode(encrypted_data).decode()

    @staticmethod
    def decrypt(encrypted_text: str, password: str) -> str:
        """
        Decrypt base64-encoded ciphertext with AES-256-GCM.

        Expects: base64(salt + nonce + ciphertext + tag)
        """
        try:
            encrypted_data = base64.b64decode(encrypted_text.encode())

            salt = encrypted_data[: CryptoManager.SALT_SIZE]
            nonce = encrypted_data[
                CryptoManager.SALT_SIZE : CryptoManager.SALT_SIZE + 12
            ]
            ciphertext_and_tag = encrypted_data[CryptoManager.SALT_SIZE + 12 :]

            key, _ = CryptoManager.derive_key(password, salt)
            cipher = AESGCM(key)

            plaintext = cipher.decrypt(nonce, ciphertext_and_tag, None)
            return plaintext.decode()

        except Exception as e:
            raise ValueError(f"Decryption failed: {e}") from e
