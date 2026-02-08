import pyotp

def get_2fa_code(secret: str) -> str:
    """
    Generate a TOTP 2FA code from a secret key.

    Args:
        secret: The base32-encoded TOTP secret key.

    Returns:
        The current 6-digit TOTP code.
    """
    totp = pyotp.TOTP(secret)
    return totp.now()
