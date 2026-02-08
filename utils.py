"""
Utility functions for the account generator project.

Provides logging, error formatting, Tor network management, and 2FA code generation.
"""

import time
from typing import Optional, Tuple, Dict, List

import pyotp
import requests
from stem import Signal
from stem.control import Controller
import stem.descriptor.remote

from random import choice
import string

from config import TOR_CONTROL_PORT, TOR_PORT, TOR_CONTROL_PASSWORD

from dotenv import load_dotenv 
from pathlib import Path

from os import getenv


# Your preferred exit node IPs
PREFERRED_EXIT_IPS = [
    '192.42.116.194',
    '192.42.116.180',
    '107.189.7.144',
    '185.181.60.205',
    '185.220.101.104',
]


# Load environment variables from .env file
# Check for .env in current directory first (for zipapp support)
env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback to default discovery (for development)
    try:
        load_dotenv()
    except AssertionError:
        # Can happen in zipapp if .env is missing and finding logic fails
        pass


def logger(message: str, level: int = 0) -> None:
    """
    Print a message with indentation based on level.

    Args:
        message: The message to print.
        level: Indentation level (each level adds 2 spaces).
    """
    indent = "  " * level
    print(f"{indent}{message}")


def format_error(e: Exception) -> str:
    """
    Format an exception message by removing Playwright call logs.

    Playwright exceptions include verbose call logs that clutter output.
    This function strips everything after "Call log:" for cleaner messages.

    Args:
        e: The exception to format.

    Returns:
        A cleaned error message string.
    """
    return str(e).split("Call log:")[0].strip()


def renew_tor(level: int = 0) -> Tuple[bool, Optional[str]]:
    """
    Request a new Tor circuit (new IP address).

    Connects to the Tor control port and sends a NEWNYM signal to get
    a fresh exit node and IP address.

    Args:
        level: Logging indentation level.

    Returns:
        A tuple of (success: bool, new_ip: str | None).
    """
    try:
        tor_port = int(getenv("TOR_PORT", "9150"))
        tor_control_port = int(getenv("TOR_CONTROL_PORT", "9151"))

        with Controller.from_port(port=tor_control_port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            time.sleep(5)  # Wait for new circuit to be established
            logger("✓ Tor renewed", level=level)

            # Try to get the new IP address
            ip: Optional[str] = None
            try:
                tor_proxies: Dict[str, str] = {
                    "http": f"socks5://127.0.0.1:{tor_port}",
                    "https": f"socks5://127.0.0.1:{tor_port}"
                }
                ip = get_current_ip(proxies=tor_proxies, level=level)
            except Exception:
                pass

            return True, ip

    except Exception as e:
        logger(f"✗ Failed to renew Tor: {e}", level=level)
        return False, None


def get_current_ip(
    proxies: Optional[Dict[str, str]] = None,
    timeout: int = 10,
    level: int = 0
) -> Optional[str]:
    """
    Get the current public IP address.

    Tries multiple IP lookup services until one succeeds.

    Args:
        proxies: Optional proxy dictionary for requests (e.g., for Tor).
        timeout: Request timeout in seconds.
        level: Logging indentation level.

    Returns:
        The IP address string, or None if all services fail.
    """
    if proxies is None:
        proxies = {}

    ip_services: List[str] = [
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
        'https://checkip.amazonaws.com',
        'https://ipinfo.io/ip',
        'https://ident.me'
    ]

    for service in ip_services:
        try:
            response = requests.get(
                service,
                proxies=proxies,
                timeout=timeout
            )
            if response.status_code == 200:
                ip = response.text.strip()
                logger(f"✓ Current IP: {ip}", level=level)
                return ip
        except requests.RequestException:
            continue

    logger("✗ Failed to get current IP", level=level)
    return None


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


def mask(value: str, show_chars: int = 3) -> str:
    """Mask sensitive data, showing only first few characters."""
    if not value:
        return "***"
    if len(value) <= show_chars:
        return "*" * len(value)
    return value[:show_chars] + "*" * (len(value) - show_chars)


def generate_random_string(length: int = 15, add_digits: bool = True, add_special_chars: bool = True) -> str:
    chars = string.ascii_letters
    if add_digits:
        chars += string.digits
    if add_special_chars:
        chars += "!@#$%^&*"
    return "".join(choice(chars) for _ in range(length))
