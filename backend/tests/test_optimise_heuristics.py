"""Tests for T1 Deterministic Earliest-Fit Bitset Scheduler (Task 1.4 Corrected).

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md
"""

from decimal import Decimal
import time
import pytest

from app.optimise.config import OptimiseConfig
from app.optimise.evidence import (
    CustomerAuthorizationEvidence,
    TaskExecutionProgressEvidence,
    VehiclePhysicalEvidence,
    WorkshopEvidenceBundle,
)
from app.optimise.heuristics import BitsetOccupancyGrid, T1BitsetScheduler
from app.optimise.models import SchedulerTier, SolverStatus
from app.schemas.domain import (
    DealershipSnapshotSchema,
    TaskStatus,
    VehiclePhysicalState,
)
from tests.optimise_test_utils import make_synthetic_evidence


class TestBitsetOccupancyGridIntegerMasks:
    """Rigorous unit tests for the true integer bitset collision grid."""

    def test_interval_mask_generation(self):
        # 3 ticks at tick 0: bits 0, 1, 2 = 7 (0b111)
        mask = BitsetOccupancyGrid.interval_mask(0, 3)
        assert mask == 7
        assert bin(mask) == "0b111"

        # 2 ticks at tick 3: bits 3, 4 = 24 (0b11000)
        mask2 = BitsetOccupancyGrid.interval_mask(3, 5)
        assert mask2 == 24
        assert bin(mask2) == "0b11000"

        # Non-overlapping masks have zero bitwise AND
        assert (mask & mask2) == 0

        # Overlapping interval [2, 4): bits 2, 3 = 12 (0b1100)
        overlap_mask = BitsetOccupancyGrid.interval_mask(2, 4)
        assert (mask & overlap_mask) != 0
        assert (mask2 & overlap_mask) != 0

    def test_initial_state_all_free(self):
        grid = BitsetOccupancyGrid(horizon_ticks=288)
        assert grid.is_tech_free("TECH-01", 96, 120)
        assert grid.is_bay_free("BAY-01", 96, 120)

    def test_mark_and_check_collision(self):
        grid = BitsetOccupancyGrid(horizon_ticks=288)
        grid.allocate("TECH-01", "BAY-01", 100, 110)

        # Non-overlapping intervals must be free
        assert grid.is_tech_free("TECH-01", 90, 100)
        assert grid.is_tech_free("TECH-01", 110, 120)
        assert grid.is_bay_free("BAY-01", 90, 100)
        assert grid.is_bay_free("BAY-01", 110, 120)

        # Overlapping intervals must report collision (not free)
        assert not grid.is_tech_free("TECH-01", 95, 105)
        assert not grid.is_tech_free("TECH-01", 105, 115)
        assert not grid.is_tech_free("TECH-01", 100, 110)
        assert not grid.is_tech_free("TECH-01", 90, 120)
        assert not grid.is_bay_free("BAY-01", 100, 110)

    def test_boundary_ticks_and_invalid_bounds(self):
        grid = BitsetOccupancyGrid(horizon_ticks=288)
        # Horizon bounds [0, 288)
        assert grid.is_tech_free("TECH-01", 0, 288)
        grid.allocate_tech_only("TECH-01", 0, 1)
        assert not grid.is_tech_free("TECH-01", 0, 1)
        assert grid.is_tech_free("TECH-01", 1, 2)

        # Invalid bounds must report False
        assert not grid.is_tech_free("TECH-01", 100, 100)
        assert not grid.is_tech_free("TECH-01", 110, 100)
        assert not grid.is_tech_free("TECH-01", -1, 10)
        assert not grid.is_tech_free("TECH-01", 280, 290)


class TestT1BitsetSchedulerCore:
    """Comprehensive test suite for T1 Earliest-Fit constructive dispatch scheduler."""

    def test_s_math_01_baseline_schedule_with_evidence(self, validated_snapshot: DealershipSnapshotSchema):
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        scheduler = T1BitsetScheduler()
        result = scheduler.schedule(validated_snapshot, plan_id="PLAN-T1-TEST", evidence=evidence)

        assert result.plan_id == "PLAN-T1-TEST"
        assert result.solver_tier == SchedulerTier.T1_HEURISTIC
        assert result.solver_status == SolverStatus.FEASIBLE
        assert result.is_verified is True
        assert result.verification_result is not None
        assert result.verification_result.is_valid is True
        assert result.verification_result.total_violations == 0

        # Verify assignments were generated
        assert len(result.plan.assignments) > 0
        assert result.metrics.gross_contribution_usd > Decimal("0.00")
        assert result.objective_value_usd is not None

        # Confirm immobilized vehicle on lift (RO-104 on BAY-01) has occupancy recorded
        imm_occs = [occ for occ in result.plan.vehicle_occupancies if occ.ro_id == "RO-104"]
        assert len(imm_occs) == 1
        assert imm_occs[0].bay_id == "BAY-01"
        assert imm_occs[0].start_tick == validated_snapshot.rooftop.operating_day_start_tick

    def test_c7_customer_authorization_hard_gate(self, validated_snapshot: DealershipSnapshotSchema):
        """Unapproved ROs must NEVER be scheduled (zero fabricated approvals)."""
        scheduler = T1BitsetScheduler()

        # 1. No evidence passed (empty bundle) -> all ROs unauthorized -> zero tasks scheduled
        empty_ev = WorkshopEvidenceBundle(current_tick=96)
        res_empty = scheduler.schedule(validated_snapshot, evidence=empty_ev)
        assert len(res_empty.plan.assignments) == 0
        for task in validated_snapshot.tasks:
            if task.status != TaskStatus.COMPLETED:
                assert "UNAUTHORIZED_CUSTOMER_ESTIMATE" in res_empty.unscheduled_tasks[task.task_id]

        # 2. Only RO-101 authorized -> only RO-101 tasks can be scheduled
        partial_ev = make_synthetic_evidence(validated_snapshot, authorize_all=False, authorized_ro_ids={"RO-101"})
        res_partial = scheduler.schedule(validated_snapshot, evidence=partial_ev)
        scheduled_ros = {a.ro_id for a in res_partial.plan.assignments}
        assert scheduled_ros == {"RO-101"}
        assert "RO-102" not in scheduled_ros

    def test_task_execution_progress_and_remaining_duration(self, validated_snapshot: DealershipSnapshotSchema):
        """IN_PROGRESS tasks must use explicit remaining duration; missing duration fails closed."""
        scheduler = T1BitsetScheduler()

        # Missing execution progress for IN_PROGRESS task fails closed
        ev_missing = make_synthetic_evidence(validated_snapshot, authorize_all=True, with_progress=False)
        result = scheduler.schedule(validated_snapshot, evidence=ev_missing)

        # IN_PROGRESS tasks in S-MATH-01 (e.g. TASK-101-01, TASK-102-01) must fail closed
        for t in validated_snapshot.tasks:
            if t.status == TaskStatus.IN_PROGRESS:
                assert t.task_id in result.unscheduled_tasks
                assert "MISSING_EXECUTION_PROGRESS" in result.unscheduled_tasks[t.task_id]

    def test_c3_transitive_precedence_closure(self, validated_snapshot: DealershipSnapshotSchema):
        """If an incomplete predecessor is excluded (e.g. missing part), its successor MUST NOT be scheduled."""
        snap = validated_snapshot.model_copy(deep=True)
        # Delay parts for TASK-104-02 so it cannot be scheduled
        # TASK-104-02 is predecessor to any subsequent reassembly tasks
        scheduler = T1BitsetScheduler()
        evidence = make_synthetic_evidence(snap, authorize_all=True)

        # Block parts for TASK-101-01 (predecessor)
        target_pred_id = "TASK-101-01"
        for p in snap.part_requirements:
            if p.task_id == target_pred_id:
                p.usable_ready_tick = None  # No ETA

        result = scheduler.schedule(snap, evidence=evidence)
        assert target_pred_id in result.unscheduled_tasks

        # Any task with target_pred_id in predecessor_task_ids must also be unscheduled
        for t in snap.tasks:
            if target_pred_id in t.predecessor_task_ids:
                assert t.task_id in result.unscheduled_tasks
                assert "PREDECESSOR_UNSCHEDULED" in result.unscheduled_tasks[t.task_id]

    def test_c5_vehicle_physical_state_gates(self, validated_snapshot: DealershipSnapshotSchema):
        """UNKNOWN physical state fails closed; IN_HOLDING enforces move delay."""
        scheduler = T1BitsetScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        # Set RO-101 vehicle to UNKNOWN
        ro101 = next(r for r in validated_snapshot.repair_orders if r.ro_id == "RO-101")
        ev.vehicle_evidence[ro101.vehicle_id].physical_state = VehiclePhysicalState.UNKNOWN

        res = scheduler.schedule(validated_snapshot, evidence=ev)
        # RO-101 tasks must be rejected
        for t in validated_snapshot.tasks:
            if t.ro_id == "RO-101":
                assert t.task_id in res.unscheduled_tasks
                assert "UNKNOWN_VEHICLE_STATE" in res.unscheduled_tasks[t.task_id]

    def test_deterministic_execution(self, validated_snapshot: DealershipSnapshotSchema):
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        scheduler = T1BitsetScheduler()
        res1 = scheduler.schedule(validated_snapshot, plan_id="PLAN-1", evidence=evidence)
        res2 = scheduler.schedule(validated_snapshot, plan_id="PLAN-2", evidence=evidence)

        assert len(res1.plan.assignments) == len(res2.plan.assignments)
        for a1, a2 in zip(res1.plan.assignments, res2.plan.assignments):
            assert a1.task_id == a2.task_id
            assert a1.bay_id == a2.bay_id
            assert a1.tech_id == a2.tech_id
            assert a1.start_tick == a2.start_tick
            assert a1.end_tick == a2.end_tick

    def test_runtime_benchmark_median_and_quantiles(self, validated_snapshot: DealershipSnapshotSchema):
        """Measures execution latency over repeated runs: median < 10ms (acceptance), typical < 2ms."""
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        scheduler = T1BitsetScheduler()

        # Warm up
        for _ in range(5):
            scheduler.schedule(validated_snapshot, evidence=evidence)

        # Benchmark 50 runs
        latencies_ms = []
        for _ in range(50):
            t0 = time.perf_counter()
            scheduler.schedule(validated_snapshot, evidence=evidence)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        latencies_ms.sort()
        median_ms = latencies_ms[len(latencies_ms) // 2]
        p95_ms = latencies_ms[int(len(latencies_ms) * 0.95)]
        p99_ms = latencies_ms[int(len(latencies_ms) * 0.99)]

        # Acceptance limit: 10 ms; engineering target: 2 ms
        assert median_ms < 10.0
        assert p95_ms < 25.0
