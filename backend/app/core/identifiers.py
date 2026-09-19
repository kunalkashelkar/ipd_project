# ============================================================
# Public URL Identifiers
# ============================================================
# Generates short, opaque, non-sequential, cryptographically random
# identifiers for external URL routing (e.g. prj_..., scn_...).
# Internal primary keys remain UUIDs.
# ============================================================

from __future__ import annotations

import re
import secrets

PREFIX_PROJECT = "prj"
PREFIX_SCAN = "scn"
PREFIX_SNAPSHOT = "snp"
PREFIX_REPORT = "rpt"
PREFIX_FINDING = "fnd"
PREFIX_NOTIFICATION = "ntf"
PREFIX_PR_RESULT = "pr"

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
PUBLIC_ID_PATTERN = re.compile(r"^(prj|scn|snp|rpt|fnd|ntf|pr)_[a-z0-9]{12}$", re.I)


def generate_public_id(prefix: str, length: int = 12) -> str:
    """Generate a non-guessable, URL-safe random public identifier."""
    token = "".join(secrets.choice(ALPHABET) for _ in range(length))
    return f"{prefix}_{token}"


def is_valid_uuid(val: str | None) -> bool:
    """Check if the string representation is a standard RFC 4122 UUID."""
    if not val:
        return False
    return bool(UUID_PATTERN.match(str(val).strip()))


def is_public_id(val: str | None) -> bool:
    """Check if the string matches the public identifier format."""
    if not val:
        return False
    return bool(PUBLIC_ID_PATTERN.match(str(val).strip()))


def parse_public_id(val: str | None) -> tuple[str, str] | None:
    """Parse prefix and token from a public identifier."""
    if not val or not is_public_id(val):
        return None
    prefix, token = val.split("_", 1)
    return prefix, token
