"""Unit and integration tests for S-MATH-01 synthetic fixture validation."""

import pytest
from app.data.loader import load_fixture_data, load_fixture_raw
from app.fixtures import S_MATH_01_FIXTURE_PATH
from app.schemas.domain import DealershipSnapshotSchema


class TestSMATH01FixtureValidation:
    """Validates the synthetic S-MATH-01 dataset structure, counts, and referential integrity."""

    def test_fixture_file_exists_and_parses(self):
        raw_data = load_fixture_raw(S_MATH_01_FIXTURE_PATH)
        assert isinstance(raw_data, dict)
        assert "rooftop" in raw_data
        assert "bays" in raw_data
        assert "technicians" in raw_data
        assert "repair_orders" in raw_data
        assert "tasks" in raw_data

    def test_fixture_entity_counts(self, validated_snapshot: DealershipSnapshotSchema):
        # 1 Rooftop
        assert validated_snapshot.rooftop.rooftop_id == "ROOF-01"

        # Exactly 3 bays
        assert len(validated_snapshot.bays) == 3
        bay_ids = {b.bay_id for b in validated_snapshot.bays}
        assert bay_ids == {"BAY-01", "BAY-02", "BAY-03"}

        # Exactly 4 technicians
        assert len(validated_snapshot.technicians) == 4
        tech_ids = {t.tech_id for t in validated_snapshot.technicians}
        assert tech_ids == {"TECH-01", "TECH-02", "TECH-03", "TECH-04"}

        # Exactly 6 repair orders
        assert len(validated_snapshot.repair_orders) == 6
        ro_ids = {r.ro_id for r in validated_snapshot.repair_orders}
        assert ro_ids == {"RO-101", "RO-102", "RO-103", "RO-104", "RO-105", "RO-106"}

        # Exactly 7 tasks (RO-104 has completed teardown + stalled reassembly)
        assert len(validated_snapshot.tasks) == 7

        # Exactly 5 part requirements
        assert len(validated_snapshot.part_requirements) == 5

        # Exactly 2 supplier offers (S1 Hotshot and S2 Sister Store)
        assert len(validated_snapshot.supplier_offers) == 2
        supplier_ids = {s.supplier_id for s in validated_snapshot.supplier_offers}
        assert supplier_ids == {"S1_HOTSHOT", "S2_SISTER_STORE"}

    def test_ro_104_disruption_state(self, validated_snapshot: DealershipSnapshotSchema):
        ro_104 = next(r for r in validated_snapshot.repair_orders if r.ro_id == "RO-104")
        assert ro_104.status.value == "STALLED"
        assert ro_104.physical_state.value == "IMMOBILIZED_ON_LIFT"
        assert ro_104.assigned_bay_id == "BAY-01"

        # Check tasks for RO-104
        tasks_104 = [t for t in validated_snapshot.tasks if t.ro_id == "RO-104"]
        assert len(tasks_104) == 2
        teardown = next(t for t in tasks_104 if t.task_id == "TASK-104-01")
        reassembly = next(t for t in tasks_104 if t.task_id == "TASK-104-02")
        assert teardown.status.value == "COMPLETED"
        assert reassembly.status.value == "STALLED"
        assert "TASK-104-01" in reassembly.predecessor_task_ids

    def test_zero_real_pii_or_vins(self, validated_snapshot: DealershipSnapshotSchema):
        for ro in validated_snapshot.repair_orders:
            assert ro.vehicle_id.startswith("VEH-SYNTH-")
            assert ro.customer_id.startswith("CUST-SYNTH-")
            # Verify vehicle is not a bay
            assert ro.vehicle_id != ro.assigned_bay_id

    def test_snapshot_hash_populated(self, validated_snapshot: DealershipSnapshotSchema):
        assert validated_snapshot.snapshot_hash is not None
        assert len(validated_snapshot.snapshot_hash) == 64
