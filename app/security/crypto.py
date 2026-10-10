"""Cryptographic primitives for session vault using scrypt and AES-GCM."""
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC_HEADER = b"GR1"
SALT_SIZE = 32
NONCE_SIZE = 12
KEY_SIZE = 32


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive 256-bit symmetric encryption key using memory-hard scrypt KDF."""
    return hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024,
        dklen=KEY_SIZE,
    )


def encrypt_payload(data: bytes, passphrase: str) -> bytes:
    """Encrypt payload using memory-hard key derivation and AES-256-GCM."""
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, MAGIC_HEADER)
    return MAGIC_HEADER + salt + nonce + ciphertext


def decrypt_payload(encrypted_blob: bytes, passphrase: str) -> bytes:
    """Decrypt payload and authenticate associated data.

    Raises ValueError on invalid format or decryption failure.
    """
    if len(encrypted_blob) < len(MAGIC_HEADER) + SALT_SIZE + NONCE_SIZE + 16:
        raise ValueError("Encrypted blob is too short")

    header = encrypted_blob[:len(MAGIC_HEADER)]
    if header != MAGIC_HEADER:
        raise ValueError("Invalid magic header")

    offset = len(MAGIC_HEADER)
    salt = encrypted_blob[offset:offset + SALT_SIZE]
    offset += SALT_SIZE
    nonce = encrypted_blob[offset:offset + NONCE_SIZE]
    offset += NONCE_SIZE
    ciphertext = encrypted_blob[offset:]

    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, MAGIC_HEADER)
    except Exception as exc:
        msg = "Decryption failed: incorrect passphrase or corrupted data"
        raise ValueError(msg) from exc
