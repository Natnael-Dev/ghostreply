"""Callback token generation and constant-time authentication."""
import hashlib
import hmac
import secrets
from typing import Tuple


def generate_callback_token() -> str:
    """Generate 8-byte URL-safe cryptographically secure token."""
    return secrets.token_urlsafe(8)


def hash_callback_token(token: str) -> str:
    """Compute SHA-256 digest of token string."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_callback_token(supplied_token: str, stored_hash: str) -> bool:
    """Constant-time verification of token against server-side hash."""
    candidate_hash = hash_callback_token(supplied_token)
    return hmac.compare_digest(candidate_hash, stored_hash)


def create_scoped_action_token(action: str, draft_id: int, token: str) -> str:
    """Format compact scoped callback token string (action:draft_id:token)."""
    return f"{action}:{draft_id}:{token}"


def parse_scoped_action_token(scoped_str: str) -> Tuple[str, int, str]:
    """Parse scoped token format into (action, draft_id, token)."""
    parts = scoped_str.split(":")
    if len(parts) != 3:
        raise ValueError("Invalid scoped action token format")
    action, draft_id_str, token = parts
    return action, int(draft_id_str), token
