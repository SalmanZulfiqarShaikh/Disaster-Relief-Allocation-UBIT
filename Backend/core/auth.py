
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Optional, Tuple

from core import config

logger = logging.getLogger("safezone.auth")

HASH_NAME = "sha256"
ITERATIONS = 600_000
SALT_BYTES = 16

SESSION_COOKIE = "safezone_session"


class AuthError(Exception):
    pass


def hash_password(password: str, *, salt: Optional[bytes] = None) -> str:
    if not password:
        raise AuthError("Password must not be empty.")

    salt = salt or _random_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, ITERATIONS)
    return "$".join(
        ["pbkdf2_sha256", str(ITERATIONS), _b64(salt), _b64(digest)]
    )


def verify_password(password: str, stored: str) -> bool:
    if not password or not stored:
        return False

    try:
        algorithm, iterations, salt_b64, expected_b64 = stored.split("$")
    except ValueError:
        logger.error("ADMIN_PASSWORD_HASH is malformed. Re-run scripts/hash_password.py.")
        return False

    if algorithm != "pbkdf2_sha256":
        logger.error("ADMIN_PASSWORD_HASH uses unknown algorithm %r.", algorithm)
        return False

    try:
        salt = _unb64(salt_b64)
        expected = _unb64(expected_b64)
        rounds = int(iterations)
    except (ValueError, TypeError):
        logger.error("ADMIN_PASSWORD_HASH is malformed. Re-run scripts/hash_password.py.")
        return False

    candidate = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(candidate, expected)


def issue_session(email: str, *, ttl_hours: Optional[int] = None) -> Tuple[str, int]:
    secret = _secret()
    hours = ttl_hours if ttl_hours is not None else config.SESSION_TTL_HOURS
    max_age = max(1, int(hours)) * 3600
    expires = int(time.time()) + max_age

    payload = f"{email}|{expires}"
    signature = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload}|{_b64(signature)}", max_age


def read_session(token: Optional[str]) -> Optional[str]:
    if not token:
        return None

    try:
        email, expires_raw, signature_b64 = token.rsplit("|", 2)
        expires = int(expires_raw)
        signature = _unb64(signature_b64)
    except (ValueError, TypeError):
        return None

    expected = hmac.new(
        _secret(), f"{email}|{expires}".encode("utf-8"), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(signature, expected):
        return None

    if expires < time.time():
        return None

    if email.lower() not in config.admin_emails():
        return None

    return email


def authenticate(email: str, password: str) -> str:
    if not is_configured():
        raise AuthError(
            "Admin login is not configured on this server. Set ADMIN_EMAILS, "
            "ADMIN_PASSWORD_HASH and SESSION_SECRET."
        )

    given = (email or "").strip().lower()

    email_ok = False
    for candidate in config.admin_emails():
        if hmac.compare_digest(given, candidate):
            email_ok = True
    password_ok = verify_password(password or "", config.ADMIN_PASSWORD_HASH)

    if not (email_ok and password_ok):
        raise AuthError("Email or password is incorrect.")

    return given


def is_configured() -> bool:
    return bool(
        config.admin_emails()
        and config.ADMIN_PASSWORD_HASH.strip()
        and config.SESSION_SECRET.strip()
    )


def _secret() -> bytes:
    secret = config.SESSION_SECRET.strip()
    if not secret:
        raise AuthError("SESSION_SECRET is not set.")
    return secret.encode("utf-8")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _random_bytes(count: int) -> bytes:
    import secrets

    return secrets.token_bytes(count)
