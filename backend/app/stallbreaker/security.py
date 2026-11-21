"""HMAC-SHA256 Cryptographic Signature Verification for Webhook Telemetry.

Authoritative Reference:
- docs/09_API_AND_MODULE_CONTRACTS.md
- docs/12_VERIFICATION_AND_REVALIDATION.md

Guarantees:
1. Constant-time comparison using hmac.compare_digest to prevent timing attacks.
2. Canonical JSON stringification for signature computation over payload dicts.
3. Rejection of blank, malformed, or tampered signatures.
"""

import hashlib
import hmac
import json
from typing import Any, Dict, Union

DEFAULT_WEBHOOK_SECRET: str = "sy-hackathon-stallbreaker-secret-2026"


def compute_hmac_sha256(
    data: Union[bytes, str, Dict[str, Any]],
    secret: str = DEFAULT_WEBHOOK_SECRET,
) -> str:
    """Computes an HMAC-SHA256 hexadecimal digest for raw bytes, string, or canonical JSON dict."""
    if isinstance(data, dict):
        raw_bytes = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    elif isinstance(data, str):
        raw_bytes = data.encode("utf-8")
    else:
        raw_bytes = data

    secret_bytes = secret.encode("utf-8")
    return hmac.new(secret_bytes, raw_bytes, hashlib.sha256).hexdigest()


def verify_hmac_sha256(
    data: Union[bytes, str, Dict[str, Any]],
    signature: str,
    secret: str = DEFAULT_WEBHOOK_SECRET,
) -> bool:
    """Verifies that the provided signature matches the computed HMAC-SHA256 digest in constant time."""
    if not signature or not isinstance(signature, str) or signature.strip() == "":
        return False

    expected_signature = compute_hmac_sha256(data, secret)
    return hmac.compare_digest(expected_signature.lower().strip(), signature.lower().strip())
