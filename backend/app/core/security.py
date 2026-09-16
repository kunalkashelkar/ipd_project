# ============================================================
# Security Utilities — Cryptography, Tokens, Hashes
# ============================================================

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from backend.app.core.config import get_settings
from backend.app.core.exceptions import AuthenticationError

# ── Password Hashing ──────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt (safe 72-byte limit)."""
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        pw_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False


# ── Cryptographic Random Tokens & Hashes ───────────────────


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a URL-safe cryptographically random token string."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a secret token for secure database persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate an API key returning (full_secret_key, display_prefix, hash_for_db).

    Key format: xai_live_<16-char-prefix>_<32-char-random>
    """
    prefix_rnd = secrets.token_hex(6)
    prefix = f"xai_{prefix_rnd}"
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}_{secret}"
    key_hash = hash_token(full_key)
    return full_key, prefix, key_hash


# ── JWT Tokens ─────────────────────────────────────────────


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived access token."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived refresh token."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Raises AuthenticationError on invalid or expired tokens.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc


def create_token_pair(
    user_id: str,
    email: str,
    session_id: str | None = None,
    active_org_id: str | None = None,
) -> dict[str, str]:
    """Create both access and refresh tokens linked to a server-side session."""
    data = {"sub": user_id, "email": email}
    if session_id:
        data["sid"] = session_id
    if active_org_id:
        data["org_id"] = active_org_id

    return {
        "access_token": create_access_token(data),
        "refresh_token": create_refresh_token(data),
        "token_type": "bearer",
    }
