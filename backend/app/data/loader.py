"""Deterministic Fixture Loading and Pydantic v2 Ingestion Pipeline."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.snapshot import compute_snapshot_hash_from_dict
from app.fixtures import S_MATH_01_FIXTURE_PATH
from app.schemas.domain import DealershipSnapshotSchema


def load_fixture_raw(path: Optional[Path] = None) -> Dict[str, Any]:
    """Reads raw JSON fixture from file path."""
    fixture_path = path or S_MATH_01_FIXTURE_PATH
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found at: {fixture_path}")
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_fixture_data(path: Optional[Path] = None) -> DealershipSnapshotSchema:
    """Loads, validates, and computes the deterministic snapshot hash for a fixture.
    
    Returns:
        Validated DealershipSnapshotSchema instance with snapshot_hash populated.
    """
    raw_data = load_fixture_raw(path)
    
    # Compute deterministic SHA-256 snapshot hash over raw payload
    computed_hash = compute_snapshot_hash_from_dict(raw_data)
    raw_data["snapshot_hash"] = computed_hash
    
    # Full Pydantic v2 validation including referential integrity checks
    validated_snapshot = DealershipSnapshotSchema.model_validate(raw_data)
    return validated_snapshot
