"""AES-GCM encryption for OAuth tokens.

Wire format: nonce (12 bytes) || GCM ciphertext.

Key source: ``settings.oauth_encryption_key`` (64-char hex = 32-byte AES-256).
If the setting is empty (dev-only), an ephemeral in-process key is used — tokens
will not survive a process restart.  In production, set the env var and optionally
replace ``_key_bytes`` with a KMS-vended Data Encryption Key call.
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_LEN = 12

# Dev-only ephemeral key — overridden by ``settings.oauth_encryption_key`` in prod.
_DEV_KEY: bytes = os.urandom(32)


def _key_bytes(key_hex: str) -> bytes:
    if key_hex:
        return bytes.fromhex(key_hex)
    return _DEV_KEY


def encrypt_token(key_hex: str, plaintext: str) -> bytes:
    """Return nonce || ciphertext; raises ValueError on bad key."""
    nonce = os.urandom(_NONCE_LEN)
    ct = AESGCM(_key_bytes(key_hex)).encrypt(nonce, plaintext.encode(), None)
    return nonce + ct


def decrypt_token(key_hex: str, ciphertext: bytes) -> str:
    """Return plaintext; raises cryptography.exceptions.InvalidTag on tampering."""
    nonce, ct = ciphertext[:_NONCE_LEN], ciphertext[_NONCE_LEN:]
    return AESGCM(_key_bytes(key_hex)).decrypt(nonce, ct, None).decode()
