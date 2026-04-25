"""Optional field-level encryption for PII (emails, API keys).

Disabled by default. To enable:
  1. Generate a key:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  2. Add ENCRYPTION_KEY=<output> and ENCRYPT_PII=true to .env

When ENCRYPT_PII is false (default), encrypt_field/decrypt_field are no-ops so
existing plaintext data remains readable without any migration.
"""
import os

ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
ENCRYPT_PII: bool = os.getenv("ENCRYPT_PII", "false").lower() == "true"


def encrypt_field(plaintext: str) -> str:
    """Encrypt a PII field. Returns plaintext unchanged when ENCRYPT_PII=false."""
    if not ENCRYPT_PII or not ENCRYPTION_KEY:
        return plaintext
    try:
        from cryptography.fernet import Fernet
        return Fernet(ENCRYPTION_KEY.encode()).encrypt(plaintext.encode()).decode()
    except Exception:
        return plaintext


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a PII field. Returns ciphertext unchanged when ENCRYPT_PII=false."""
    if not ENCRYPT_PII or not ENCRYPTION_KEY:
        return ciphertext
    try:
        from cryptography.fernet import Fernet
        return Fernet(ENCRYPTION_KEY.encode()).decrypt(ciphertext.encode()).decode()
    except Exception:
        return ciphertext
