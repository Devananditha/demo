"""Unit tests for Pydantic v2 Canonical Domain Validation Schemas."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.core.time_utils import (
    HORIZON_TICKS,
    minutes_to_ticks,
    tick_to_minutes,
    tick_to_time_str,
    time_str_to_tick,
)
from app.schemas.domain import (
    BaySchema,
    BayType,
    DealershipSnapshotSchema,
    PartInventoryStatus,
    PartRequirementSchema,
    QuoteStatus,
    RepairOrderSchema,
    ROStatus,
    RooftopSchema,
    SkillCode,
    SupplierOfferSchema,
    TaskSchema,
    TaskStatus,
    VehiclePhysicalState,
)


class TestTimeUtils:
    """Test canonical time conventions and conversion utilities."""

    def test_tick_conversions(self):
        assert tick_to_minutes(0) == 0
        assert tick_to_minutes(96) == 480  # 8 * 60
        assert tick_to_minutes(204) == 1020  # 17 * 60
        assert tick_to_minutes(288) == 1440

        assert minutes_to_ticks(0) == 0
        assert minutes_to_ticks(480) == 96
        assert minutes_to_ticks(1020) == 204

    def test_time_str_conversions(self):
        assert time_str_to_tick("08:00") == 96
        assert time_str_to_tick("13:15") == 159
        assert time_str_to_tick("17:00") == 204

        assert tick_to_time_str(96) == "08:00"
        assert tick_to_time_str(159) == "13:15"
        assert tick_to_time_str(204) == "17:00"

    def test_invalid_tick_raises(self):
        with pytest.raises(ValueError, match="outside valid horizon"):
            tick_to_minutes(-1)
        with pytest.raises(ValueError, match="outside valid horizon"):
            tick_to_minutes(289)

    def test_invalid_time_str_raises(self):
        with pytest.raises(ValueError, match="Invalid time format"):
            time_str_to_tick("25:00")
        with pytest.raises(ValueError, match="Invalid time format"):
            time_str_to_tick("invalid")


class TestRooftopSchema:
    """Test Rooftop schema validation rules."""

    def test_valid_rooftop(self):
        now = datetime.now(timezone.utc)
        rooftop = RooftopSchema(
            rooftop_id="ROOF-01",
            name="Test Dealership",
            timezone="America/New_York",
            operating_day_start_tick=96,
            operating_day_end_tick=204,
            overtime_cutoff_tick=228,
            version=1,
            created_at=now,
            updated_at=now,
        )
        assert rooftop.rooftop_id == "ROOF-01"
        assert rooftop.operating_day_start_tick == 96

    def test_naive_timestamp_rejected(self):
        naive_now = datetime.utcnow()  # no tzinfo
        with pytest.raises(ValidationError, match="timezone-aware"):
            RooftopSchema(
                rooftop_id="ROOF-01",
                name="Test",
                created_at=naive_now,
                updated_at=naive_now,
            )

    def test_invalid_operating_hours_rejected(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError, match="strictly less than"):
            RooftopSchema(
                rooftop_id="ROOF-01",
                name="Test",
                operating_day_start_tick=204,
                operating_day_end_tick=96,
                created_at=now,
                updated_at=now,
            )


class TestBaySchema:
    """Test Bay schema validation rules."""

    def test_valid_bay(self):
        bay = BaySchema(
            bay_id="BAY-01",
            rooftop_id="ROOF-01",
            name="Lift 1",
            bay_type=BayType.HEAVY_DIAGNOSTIC_LIFT.value,
            lifting_capacity_lbs=12000,
            is_operational=True,
            version=1,
        )
        assert bay.lifting_capacity_lbs == 12000

    def test_negative_capacity_rejected(self):
        with pytest.raises(ValidationError):
            BaySchema(
                bay_id="BAY-01",
                rooftop_id="ROOF-01",
                name="Lift 1",
                bay_type="STANDARD_2POST",
                lifting_capacity_lbs=-500,
                version=1,
            )


class TestTechnicianSchema:
    """Test Technician schema validation rules."""

    def test_lunch_outside_shift_rejected(self):
        from app.schemas.domain import TechnicianSchema
        with pytest.raises(ValidationError, match="must fall entirely within shift"):
            TechnicianSchema(
                tech_id="TECH-01",
                rooftop_id="ROOF-01",
                display_name="Alex",
                skill_certifications=["EV"],
                shift_start_tick=96,
                shift_end_tick=204,
                lunch_start_tick=200,  # lunch 200..212 extends past 204
                lunch_duration_ticks=12,
                version=1,
            )

    def test_empty_skills_rejected(self):
        from app.schemas.domain import TechnicianSchema
        with pytest.raises(ValidationError):
            TechnicianSchema(
                tech_id="TECH-01",
                rooftop_id="ROOF-01",
                display_name="Alex",
                skill_certifications=[],  # empty skills list
                shift_start_tick=96,
                shift_end_tick=204,
                lunch_start_tick=144,
                version=1,
            )


class TestRepairOrderSchema:
    """Test RepairOrder validation rules."""

    def test_valid_repair_order(self):
        now = datetime.now(timezone.utc)
        ro = RepairOrderSchema(
            ro_id="RO-104",
            rooftop_id="ROOF-01",
            vehicle_id="VEH-104",
            customer_id="CUST-104",
            complaint="Transmission slip",
            promised_at=now,
            promise_tick=192,
            priority_weight=3,
            status=ROStatus.STALLED,
            physical_state=VehiclePhysicalState.IMMOBILIZED_ON_LIFT,
            assigned_bay_id="BAY-01",
            version=1,
            updated_at=now,
        )
        assert ro.status == ROStatus.STALLED
        assert ro.physical_state == VehiclePhysicalState.IMMOBILIZED_ON_LIFT

    def test_invalid_status_rejected(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            RepairOrderSchema(
                ro_id="RO-104",
                rooftop_id="ROOF-01",
                vehicle_id="VEH-104",
                customer_id="CUST-104",
                complaint="Brakes",
                promised_at=now,
                promise_tick=192,
                status="INVALID_STATUS",
                physical_state=VehiclePhysicalState.ROLLABLE,
                updated_at=now,
            )


class TestSupplierOfferSchema:
    """Test SupplierOffer validation rules."""

    def test_usable_before_eta_rejected(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError, match="cannot be earlier than quoted_eta_tick"):
            SupplierOfferSchema(
                offer_id="OFFER-01",
                part_req_id="PART-01",
                supplier_id="S1",
                supplier_name="Hotshot",
                unit_cost_usd=Decimal("120.00"),
                freight_surcharge_usd=Decimal("37.00"),
                quoted_eta_tick=165,
                receiving_inspection_minutes=15,
                usable_ready_tick=160,  # earlier than ETA!
                quote_valid_until=now,
                quote_status=QuoteStatus.ACTIVE,
                version=1,
            )

    def test_negative_cost_rejected(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            SupplierOfferSchema(
                offer_id="OFFER-01",
                part_req_id="PART-01",
                supplier_id="S1",
                supplier_name="Hotshot",
                unit_cost_usd=Decimal("-50.00"),
                freight_surcharge_usd=Decimal("0.00"),
                quoted_eta_tick=160,
                usable_ready_tick=165,
                quote_valid_until=now,
                version=1,
            )
