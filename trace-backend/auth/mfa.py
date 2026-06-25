import pyotp
import string
import secrets
from typing import List

def generate_totp_secret() -> str:
    """Generate a base32 TOTP secret key"""
    return pyotp.random_base32()

def verify_totp(secret: str, otp: str) -> bool:
    """Verify TOTP code with a 30-second window, allowing ±1 step drift"""
    if not secret or not otp:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(otp, valid_window=1)

def generate_backup_codes(count=8) -> List[str]:
    """Generate single-use 8-character alphanumeric backup codes"""
    alphabet = string.ascii_letters + string.digits
    codes = []
    for _ in range(count):
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        codes.append(code)
    return codes
