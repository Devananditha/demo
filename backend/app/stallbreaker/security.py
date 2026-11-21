"""HMAC-SHA256 Cryptographic Signature Verification and Replay Protection.

Authoritative Reference:
- docs/09_API_AND_MODULE_CONTRACTS.md
- docs/12_VERIFICATION_AND_REVALIDATION.md

Guarantees:
1. Constant-time comparison using hmac.compare_digest to prevent timing attacks.
2. Production enforcement: Unsigned events are rejected when REQUIRE_HMAC=true or ENVIRONMENT=production.
3. Replay protection: Event timestamp skew check prevents replay attacks.
4. Canonical JSON stringification for deterministic signature evaluation.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from typing import Any, Dict, Optional, Union

DEFAULT_WEBHOOK_SECRET: str = os.getenv("STALLBREAKER_HMAC_SECRET", "sy-hackathon-stallbreaker-secret-2026")
MAX_EVENT_SKEW_SECONDS: int = int(os.getenv("MAX_EVENT_SKEW_SECONDS", "300"))  # 5 minutes


def is_production_mode() -> bool:
    """True if HMAC signature enforcement is mandatory in current deployment environment."""
    env = os.getenv("ENVIRONMENT", os.getenv("SERVICE_ENV", "development")).lower()
    require_hmac = os.getenv("REQUIRE_HMAC", "false").lower() in ("true", "1", "yes")
    return require_hmac or env in ("production", "prod")


def compute_hmac_sha256(
    data: Union[bytes, str, Dict[str, Any]],
    secret: Optional[str] = None,
) -> str:
    """Computes an HMAC-SHA256 hexadecimal digest for raw bytes, string, or canonical JSON dict."""
    effective_secret = secret or os.getenv("STALLBREAKER_HMAC_SECRET", DEFAULT_WEBHOOK_SECRET)
    if isinstance(data, dict):
        raw_bytes = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    elif isinstance(data, str):
        raw_bytes = data.encode("utf-8")
    else:
        raw_bytes = data

    secret_bytes = effective_secret.encode("utf-8")
    return hmac.new(secret_bytes, raw_bytes, hashlib.sha256).hexdigest()


def verify_hmac_sha256(
    data: Union[bytes, str, Dict[str, Any]],
    signature: Optional[str],
    secret: Optional[str] = None,
) -> bool:
    """Verifies that the provided signature matches the computed HMAC-SHA256 digest in constant time."""
    if not signature or not isinstance(signature, str) or signature.strip() == "":
        return False

    expected_signature = compute_hmac_sha256(data, secret)
    return hmac.compare_digest(expected_signature.lower().strip(), signature.lower().strip())


def validate_event_timestamp(
    occurred_at: datetime,
    max_skew_seconds: int = MAX_EVENT_SKEW_SECONDS,
) -> bool:
    """Replay protection: verifies event occurred within allowable clock skew window."""
    now = datetime.now(timezone.utc)
    target_dt = occurred_at if occurred_at.tzinfo else occurred_at.replace(tzinfo=timezone.utc)
    skew = abs((now - target_dt).total_seconds())
    return skew <= max_skew_seconds
