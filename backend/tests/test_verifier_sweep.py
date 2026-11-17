"""Integration and Unit Tests for L4 Sweep-Line Independent Verifier."""

from decimal import Decimal
import pytest

from app.constraints.rules import ViolationCode
from app.data.loader import load_fixture_data
from app.verifier.models import CandidateSchedulePlan, ScheduledAssignment, VehicleBayOccupancy
from app.verifier.sweep_oracle import SweepLineOracle


@pytest.fixture
def snapshot():
    """Loads validated S-MATH-01 synthetic snapshot."""
    return load_fixture_data()


@pytest.fixture
def oracle(snapshot):
    """Instantiates the L4 Sweep-Line Oracle with the S-MATH-01 snapshot."""
    return SweepLineOracle(snapshot)


class TestSweepLineOracleBaseline:
    def test_valid_baseline_schedule_passes_verification(self, oracle, snapshot):
        """Constructs a certified valid baseline schedule for S-MATH-01 and asserts PASS."""
        plan = CandidateSchedulePlan(
            plan_id="PLAN-BASELINE-VERIFIED",
            rooftop_id="ROOF-01",
            snapshot_hash=snapshot.snapshot_hash or "",
            assignments=[
                # Tech-03 (Brakes/Suspension) in Bay-02
                ScheduledAssignment(
                    task_id="TASK-101-01",
                    ro_id="RO-101",
                    tech_id="TECH-03",
                    bay_id="BAY-02",
                    start_tick=96,
                    end_tick=114,
                ),
                # Tech-04 (Maintenance) in Bay-03
                ScheduledAssignment(
                    task_id="TASK-102-01",
                    ro_id="RO-102",
                    tech_id="TECH-04",
                    bay_id="BAY-03",
                    start_tick=96,
                    end_tick=108,
                ),
                # Tech-03 (Suspension) in Bay-02 (Contiguous after Task-101)
                ScheduledAssignment(
                    task_id="TASK-103-01",
                    ro_id="RO-103",
                    tech_id="TECH-03",
                    bay_id="BAY-02",
                    start_tick=114,
                    end_tick=138,
                ),
                # Tech-02 (Transmission) in Bay-01
                ScheduledAssignment(
                    task_id="TASK-104-01",
                    ro_id="RO-104",
                    tech_id="TECH-02",
                    bay_id="BAY-01",
                    start_tick=96,
                    end_tick=108,
                ),
                # Tech-01 (Diagnostic) in Bay-01 (Contiguous after Task-104-01)
                ScheduledAssignment(
                    task_id="TASK-106-01",
                    ro_id="RO-106",
                    tech_id="TECH-01",
                    bay_id="BAY-01",
                    start_tick=108,
                    end_tick=132,
                ),
            ],
            customer_authorizations={
                "RO-101": True,
                "RO-102": True,
                "RO-103": True,
                "RO-104": True,
                "RO-105": True,
                "RO-106": True,
            },
        )

        result = oracle.verify_plan(plan)
        assert result.status == "PASS"
        assert result.is_valid is True
        assert result.total_violations == 0
        assert result.execution_time_ms < 50.0  # Fast O(N log N) sweep

    def test_contiguous_handoff_on_same_resource_does_not_false_alarm(self, oracle, snapshot):
        """Proves that END event processing before START at identical ticks enables contiguous transitions."""
        plan = CandidateSchedulePlan(
            plan_id="PLAN-CONTIGUOUS-CHECK",
            rooftop_id="ROOF-01",
            snapshot_hash=snapshot.snapshot_hash or "",
            assignments=[
                # Task A: [96, 108) on Tech-03 in Bay-02
                ScheduledAssignment(
                    task_id="TASK-101-01",
                    ro_id="RO-101",
                    tech_id="TECH-03",
                    bay_id="BAY-02",
                    start_tick=96,
                    end_tick=108,
                ),
                # Task B: [108, 120) on Tech-03 in Bay-02 (starts EXACTLY when A ends)
                ScheduledAssignment(
                    task_id="TASK-103-01",
                    ro_id="RO-103",
                    tech_id="TECH-03",
                    bay_id="BAY-02",
                    start_tick=108,
                    end_tick=120,
                ),
            ],
        )
        result = oracle.verify_plan(plan)
        # Should not report C4 double-booking on either Tech-03 or Bay-02
        c4_violations = [v for v in result.violations if v.constraint == "C4"]
        assert len(c4_violations) == 0

    def test_vehicle_occupancy_blocks_bay_assignment(self, oracle, snapshot):
        """Verifies that an idle/stalled vehicle occupying a bay blocks any task assignment."""
        plan = CandidateSchedulePlan(
            plan_id="PLAN-VEHICLE-OCCUPANCY-CONFLICT",
            rooftop_id="ROOF-01",
            snapshot_hash=snapshot.snapshot_hash or "",
            assignments=[
                ScheduledAssignment(
                    task_id="TASK-106-01",
                    ro_id="RO-106",
                    tech_id="TECH-01",
                    bay_id="BAY-01",
                    start_tick=120,
                    end_tick=144,
                ),
            ],
            vehicle_occupancies=[
                # Vehicle-104 is immobilized on lift in Bay-01 from 108 to 165
                VehicleBayOccupancy(
                    vehicle_id="VEH-SYNTH-104",
                    ro_id="RO-104",
                    bay_id="BAY-01",
                    start_tick=108,
                    end_tick=165,
                )
            ],
        )
        result = oracle.verify_plan(plan)
        assert result.status == "FAIL"
        assert any(v.code == ViolationCode.C4_BAY_DOUBLE_BOOKED for v in result.violations)
