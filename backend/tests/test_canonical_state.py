"""Integration tests for SQLAlchemy 2.0 Canonical Relational State Models."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.canonical import (
    Bay,
    PartRequirement,
    RepairOrder,
    Rooftop,
    SupplierOffer,
    Task,
    Technician,
)


class TestCanonicalDatabaseModels:
    """Test persistence, relationships, and constraints in SQLAlchemy."""

    def test_create_and_query_rooftop_hierarchy(self, db_session: Session):
        now = datetime.now(timezone.utc)
        rooftop = Rooftop(
            rooftop_id="ROOF-TEST",
            name="Test Dealership",
            timezone="America/New_York",
            operating_day_start_tick=96,
            operating_day_end_tick=204,
            overtime_cutoff_tick=228,
            version=1,
            created_at=now,
            updated_at=now,
        )
        db_session.add(rooftop)
        db_session.commit()

        # Add bay and technician
        bay = Bay(
            bay_id="BAY-T1",
            rooftop_id="ROOF-TEST",
            name="Lift 1",
            bay_type="HEAVY_DIAGNOSTIC_LIFT",
            lifting_capacity_lbs=12000,
            is_operational=True,
            version=1,
        )
        tech = Technician(
            tech_id="TECH-T1",
            rooftop_id="ROOF-TEST",
            display_name="Alex",
            skill_certifications=["EV", "DIAGNOSTIC"],
            shift_start_tick=96,
            shift_end_tick=204,
            lunch_start_tick=144,
            lunch_duration_ticks=12,
            is_active=True,
            version=1,
        )
        db_session.add_all([bay, tech])
        db_session.commit()

        # Add Repair Order
        ro = RepairOrder(
            ro_id="RO-T101",
            rooftop_id="ROOF-TEST",
            vehicle_id="VEH-T1",
            customer_id="CUST-T1",
            complaint="Brakes",
            promised_at=now,
            promise_tick=144,
            priority_weight=2,
            status="IN_PROGRESS",
            physical_state="IMMOBILIZED_ON_LIFT",
            assigned_bay_id="BAY-T1",
            version=1,
            updated_at=now,
        )
        db_session.add(ro)
        db_session.commit()

        # Add Task
        task = Task(
            task_id="TASK-T101-01",
            ro_id="RO-T101",
            sequence_order=1,
            operation_code="BRK-01",
            description="Replace pads",
            required_skill="BRAKES",
            required_bay_type="HEAVY_DIAGNOSTIC_LIFT",
            flat_rate_minutes=90,
            estimated_duration_ticks=18,
            status="IN_PROGRESS",
            predecessor_task_ids=[],
            version=1,
        )
        db_session.add(task)
        db_session.commit()

        # Add PartRequirement and SupplierOffer
        part = PartRequirement(
            part_req_id="PART-T1",
            ro_id="RO-T101",
            task_id="TASK-T101-01",
            oem_part_number="OEM-12345",
            quantity=1,
            inventory_status="IN_TRANSIT",
            usable_ready_tick=140,
            version=1,
        )
        db_session.add(part)
        db_session.commit()

        offer = SupplierOffer(
            offer_id="OFFER-T1",
            part_req_id="PART-T1",
            supplier_id="S1",
            supplier_name="Hotshot Courier",
            unit_cost_usd=Decimal("120.00"),
            freight_surcharge_usd=Decimal("37.00"),
            quoted_eta_tick=135,
            receiving_inspection_minutes=15,
            usable_ready_tick=138,
            quote_valid_until=now,
            quote_status="ACTIVE",
            version=1,
        )
        db_session.add(offer)
        db_session.commit()

        # Verify Relationships
        queried_rooftop = db_session.get(Rooftop, "ROOF-TEST")
        assert queried_rooftop is not None
        assert len(queried_rooftop.bays) == 1
        assert len(queried_rooftop.technicians) == 1
        assert len(queried_rooftop.repair_orders) == 1
        
        queried_ro = queried_rooftop.repair_orders[0]
        assert queried_ro.assigned_bay.bay_id == "BAY-T1"
        assert len(queried_ro.tasks) == 1
        assert len(queried_ro.part_requirements) == 1
        assert len(queried_ro.part_requirements[0].supplier_offers) == 1

    def test_foreign_key_cascade_deletion(self, db_session: Session):
        now = datetime.now(timezone.utc)
        rooftop = Rooftop(
            rooftop_id="ROOF-CASCADE",
            name="Cascade Test",
            timezone="UTC",
            created_at=now,
            updated_at=now,
        )
        bay = Bay(
            bay_id="BAY-C1",
            rooftop_id="ROOF-CASCADE",
            name="Lift C1",
            bay_type="STANDARD_2POST",
            lifting_capacity_lbs=10000,
        )
        rooftop.bays.append(bay)
        db_session.add(rooftop)
        db_session.commit()

        # Deleting rooftop cascades to bay
        db_session.delete(rooftop)
        db_session.commit()

        assert db_session.get(Rooftop, "ROOF-CASCADE") is None
        assert db_session.get(Bay, "BAY-C1") is None

    def test_check_constraint_enforcement(self, db_session: Session):
        now = datetime.now(timezone.utc)
        rooftop = Rooftop(
            rooftop_id="ROOF-CK",
            name="Check Test",
            timezone="UTC",
            created_at=now,
            updated_at=now,
        )
        db_session.add(rooftop)
        db_session.commit()

        # Attempt to insert bay with negative capacity
        bay = Bay(
            bay_id="BAY-ERR",
            rooftop_id="ROOF-CK",
            name="Invalid Bay",
            bay_type="STANDARD_2POST",
            lifting_capacity_lbs=-100,  # violates CheckConstraint
        )
        db_session.add(bay)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
