"""Unit tests for deterministic SHA-256 snapshot hashing."""

import copy
import pytest

from app.core.snapshot import (
    SNAPSHOT_SCHEMA_PREFIX,
    build_version_vector_from_entities,
    compute_snapshot_hash,
    compute_snapshot_hash_from_dict,
)
from app.data.loader import load_fixture_raw
from app.fixtures import S_MATH_01_FIXTURE_PATH


class TestSnapshotHashing:
    """Verifies determinism, permutation invariance, and mutation sensitivity."""

    def test_hash_determinism_same_data(self):
        raw_1 = load_fixture_raw(S_MATH_01_FIXTURE_PATH)
        raw_2 = load_fixture_raw(S_MATH_01_FIXTURE_PATH)

        hash_1 = compute_snapshot_hash_from_dict(raw_1)
        hash_2 = compute_snapshot_hash_from_dict(raw_2)

        assert hash_1 == hash_2
        assert len(hash_1) == 64
        # Lowercase hex
        assert hash_1 == hash_1.lower()

    def test_permutation_invariance(self):
        raw_data = load_fixture_raw(S_MATH_01_FIXTURE_PATH)
        
        # Create permuted copy with reversed entity lists
        permuted_data = copy.deepcopy(raw_data)
        permuted_data["bays"] = list(reversed(permuted_data["bays"]))
        permuted_data["technicians"] = list(reversed(permuted_data["technicians"]))
        permuted_data["repair_orders"] = list(reversed(permuted_data["repair_orders"]))
        permuted_data["tasks"] = list(reversed(permuted_data["tasks"]))
        permuted_data["part_requirements"] = list(reversed(permuted_data["part_requirements"]))
        permuted_data["supplier_offers"] = list(reversed(permuted_data["supplier_offers"]))

        hash_original = compute_snapshot_hash_from_dict(raw_data)
        hash_permuted = compute_snapshot_hash_from_dict(permuted_data)

        assert hash_original == hash_permuted

    def test_mutation_sensitivity_rooftop_version(self):
        raw_data = load_fixture_raw(S_MATH_01_FIXTURE_PATH)
        base_hash = compute_snapshot_hash_from_dict(raw_data)

        mutated_data = copy.deepcopy(raw_data)
        mutated_data["rooftop"]["version"] = 2
        mutated_hash = compute_snapshot_hash_from_dict(mutated_data)

        assert mutated_hash != base_hash

    def test_mutation_sensitivity_single_ro_version(self):
        raw_data = load_fixture_raw(S_MATH_01_FIXTURE_PATH)
        base_hash = compute_snapshot_hash_from_dict(raw_data)

        mutated_data = copy.deepcopy(raw_data)
        # Bump version of RO-104 from 1 to 2
        ro_104 = next(r for r in mutated_data["repair_orders"] if r["ro_id"] == "RO-104")
        ro_104["version"] = 2
        mutated_hash = compute_snapshot_hash_from_dict(mutated_data)

        assert mutated_hash != base_hash

    def test_mutation_sensitivity_added_entity(self):
        raw_data = load_fixture_raw(S_MATH_01_FIXTURE_PATH)
        base_hash = compute_snapshot_hash_from_dict(raw_data)

        mutated_data = copy.deepcopy(raw_data)
        # Add new bay
        mutated_data["bays"].append({
            "bay_id": "BAY-NEW-04",
            "version": 1,
        })
        mutated_hash = compute_snapshot_hash_from_dict(mutated_data)

        assert mutated_hash != base_hash

    def test_direct_vector_construction(self):
        vector = build_version_vector_from_entities(
            rooftop_version=("ROOF-01", 1),
            bays=[("BAY-01", 1), ("BAY-02", 1)],
            technicians=[("TECH-01", 1)],
            repair_orders=[("RO-101", 1)],
            tasks=[("TASK-01", 1)],
        )
        h1 = compute_snapshot_hash(vector)
        # Shuffled vector
        h2 = compute_snapshot_hash(list(reversed(vector)))
        assert h1 == h2
