import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# Derive a stable URL-safe base64 key from SECRET_KEY or FIELD_ENCRYPTION_KEY
_fernet_instance = None

def get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        key_str = os.getenv("FIELD_ENCRYPTION_KEY")
        if key_str:
            # If provided as 32-byte string, encode it safely to urlsafe_b64
            if len(key_str) == 32:
                key_bytes = base64.urlsafe_b64encode(key_str.encode())
            else:
                # Ensure it's urlsafe b64
                try:
                    key_bytes = key_str.encode()
                    # Test if valid key
                    Fernet(key_bytes)
                except Exception:
                    key_bytes = base64.urlsafe_b64encode(key_str.ljust(32)[:32].encode())
        else:
            # Derive key using PBKDF2 from SECRET_KEY
            secret = os.getenv("SECRET_KEY", "fallback_secret_key_for_development_purposes_only_123456789")
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"trace_field_salt_123",
                iterations=100000
            )
            key_bytes = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
            
        _fernet_instance = Fernet(key_bytes)
    return _fernet_instance

def generate_field_key() -> bytes:
    # PBKDF2 key derivation for general use
    secret = os.getenv("SECRET_KEY", "fallback_secret_key_for_development_purposes_only_123456789")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"trace_field_salt_123",
        iterations=100000
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))

def encrypt_field(plaintext: str) -> str:
    if not plaintext:
        return ""
    f = get_fernet()
    return f.encrypt(plaintext.encode()).decode()

def decrypt_field(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    # If the field is not actually encrypted (e.g. old data or fallback), return as is
    if not (ciphertext.startswith("gAAAAA") or "|" in ciphertext):
        return ciphertext
    
    # Handle blind index formats: "blind_index|ciphertext"
    parts = ciphertext.split("|", 1)
    cipher_part = parts[1] if len(parts) == 2 else parts[0]
    
    try:
        f = get_fernet()
        return f.decrypt(cipher_part.encode()).decode()
    except Exception:
        # Return raw ciphertext if decryption fails (e.g. invalid key or non-encrypted data)
        return ciphertext

def hash_file(file_bytes: bytes) -> str:
    """SHA-256 hex digest for chain-of-custody"""
    return hashlib.sha256(file_bytes).hexdigest()

def get_blind_index(value: str) -> str:
    """Generates a deterministic hash search key for encrypted fields"""
    if not value:
        return ""
    secret = os.getenv("SECRET_KEY", "fallback_secret_key_for_development_purposes_only_123456789")
    keyed_hash = hashlib.sha256(f"{value}:{secret}".encode()).hexdigest()
    return keyed_hash

def encrypt_searchable_field(plaintext: str) -> str:
    """Encrypts a field and prefixes it with its deterministic blind index for exact queries"""
    if not plaintext:
        return ""
    blind_idx = get_blind_index(plaintext)
    ciphertext = encrypt_field(plaintext)
    return f"{blind_idx}|{ciphertext}"
