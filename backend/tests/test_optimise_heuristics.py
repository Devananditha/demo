"""Tests for T1 Deterministic Earliest-Fit Bitset Scheduler (Task 1.4).

Authoritative Reference:
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md
"""

from copy import deepcopy
from decimal import Decimal
import time
import pytest

from app.optimise.config import OptimiseConfig
from app.optimise.heuristics import BitsetOccupancyGrid, T1BitsetScheduler
from app.optimise.models import SchedulerTier, SolverStatus
from app.schemas.domain import (
    DealershipSnapshotSchema,
    PartRequirementSchema,
    TaskSchema,
    TaskStatus,
    VehiclePhysicalState,
)
from app.verifier.sweep_oracle import SweepLineOracle


class TestBitsetOccupancyGrid:
    """Unit tests for the discrete-tick bitset collision grid."""

    def test_initial_state_all_free(self):
        grid = BitsetOccupancyGrid(horizon_ticks=288)
        assert grid.is_interval_free(grid._tech_busy["TECH-01"], 96, 120)
        assert grid.is_interval_free(grid._bay_busy["BAY-01"], 96, 120)

    def test_mark_and_check_collision(self):
        grid = BitsetOccupancyGrid(horizon_ticks=288)
        grid.mark_interval_busy(grid._tech_busy["TECH-01"], 100, 110)

        # Non-overlapping intervals should be free
        assert grid.is_interval_free(grid._tech_busy["TECH-01"], 90, 100)
        assert grid.is_interval_free(grid._tech_busy["TECH-01"], 110, 120)

        # Overlapping intervals must report busy (collision)
        assert not grid.is_interval_free(grid._tech_busy["TECH-01"], 95, 105)
        assert not grid.is_interval_free(grid._tech_busy["TECH-01"], 105, 115)
        assert not grid.is_interval_free(grid._tech_busy["TECH-01"], 100, 110)
        assert not grid.is_interval_free(grid._tech_busy["TECH-01"], 90, 120)

    def test_invalid_interval_bounds(self):
        grid = BitsetOccupancyGrid(horizon_ticks=288)
        assert not grid.is_interval_free(grid._tech_busy["TECH-01"], 100, 100)
        assert not grid.is_interval_free(grid._tech_busy["TECH-01"], 110, 100)


class TestT1BitsetScheduler:
    """Comprehensive test suite for T1 Earliest-Fit constructive dispatch scheduler."""

    def test_s_math_01_baseline_schedule(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        result = scheduler.schedule(validated_snapshot, plan_id="PLAN-T1-TEST")

        assert result.plan_id == "PLAN-T1-TEST"
        assert result.solver_tier == SchedulerTier.T1_HEURISTIC
        assert result.solver_status == SolverStatus.FEASIBLE
        assert result.is_verified is True
        assert result.verification_result is not None
        assert result.verification_result.is_valid is True
        assert result.verification_result.total_violations == 0

        # Verify assignments were generated
        assert len(result.plan.assignments) > 0

        # Check metrics validity
        assert result.metrics.gross_contribution_usd > Decimal("0.00")
        assert result.objective_value_usd is not None

        # Confirm immobilized vehicle on lift (RO-104 on BAY-01) has occupancy recorded
        imm_occs = [occ for occ in result.plan.vehicle_occupancies if occ.ro_id == "RO-104"]
        assert len(imm_occs) == 1
        assert imm_occs[0].bay_id == "BAY-01"
        assert imm_occs[0].start_tick == validated_snapshot.rooftop.operating_day_start_tick

    def test_deterministic_execution(self, validated_snapshot: DealershipSnapshotSchema):
        """Scheduling twice on identical input must yield byte-for-byte identical plans."""
        scheduler = T1BitsetScheduler()
        res1 = scheduler.schedule(validated_snapshot, plan_id="PLAN-1")
        res2 = scheduler.schedule(validated_snapshot, plan_id="PLAN-2")

        assert len(res1.plan.assignments) == len(res2.plan.assignments)
        for a1, a2 in zip(res1.plan.assignments, res2.plan.assignments):
            assert a1.task_id == a2.task_id
            assert a1.bay_id == a2.bay_id
            assert a1.tech_id == a2.tech_id
            assert a1.start_tick == a2.start_tick
            assert a1.end_tick == a2.end_tick

        assert res1.objective_value_usd == res2.objective_value_usd

    def test_runtime_benchmark_sub_2ms(self, validated_snapshot: DealershipSnapshotSchema):
        """T1 scheduler must execute in under 2ms in production (assert < 50ms in test environment)."""
        scheduler = T1BitsetScheduler()
        
        # Warm up
        scheduler.schedule(validated_snapshot)

        # Benchmark
        iterations = 10
        start_t = time.perf_counter()
        for _ in range(iterations):
            scheduler.schedule(validated_snapshot)
        elapsed_per_run_ms = ((time.perf_counter() - start_t) / iterations) * 1000.0

        # Even on shared CI/CD or slow machines, it should be well under 50ms
        assert elapsed_per_run_ms < 50.0

    def test_c1_technician_skill_enforcement(self, validated_snapshot: DealershipSnapshotSchema):
        """A task requiring specific skill cannot be scheduled if no technician has that certification."""
        snap = validated_snapshot.model_copy(deep=True)
        # Strip all certifications from technicians except QUICK_SERVICE
        for tech in snap.technicians:
            tech.skill_certifications = ["QUICK_SERVICE"]

        scheduler = T1BitsetScheduler()
        result = scheduler.schedule(snap)

        # Tasks requiring specialized skills (e.g. BRAKES for TASK-101-01, MAINTENANCE for TASK-102-01) must be rejected
        assert "TASK-101-01" in result.unscheduled_tasks
        assert "NO_ELIGIBLE_TECHNICIAN_SKILL" in result.unscheduled_tasks["TASK-101-01"]
        assert "TASK-102-01" in result.unscheduled_tasks
        assert "NO_ELIGIBLE_TECHNICIAN_SKILL" in result.unscheduled_tasks["TASK-102-01"]

    def test_c1_bay_type_enforcement(self, validated_snapshot: DealershipSnapshotSchema):
        """Tasks cannot be scheduled in bays lacking required type."""
        snap = validated_snapshot.model_copy(deep=True)
        # Change all bays to DETAIL
        for bay in snap.bays:
            bay.bay_type = "DETAIL"

        scheduler = T1BitsetScheduler()
        result = scheduler.schedule(snap)

        # Tasks requiring other bay types must be rejected
        for task in snap.tasks:
            if task.status != TaskStatus.COMPLETED and task.required_bay_type != "DETAIL":
                assert task.task_id in result.unscheduled_tasks

    def test_c2_parts_arrival_gating(self, validated_snapshot: DealershipSnapshotSchema):
        """A task with parts arriving at tick 150 cannot start before tick 150."""
        snap = validated_snapshot.model_copy(deep=True)
        # Delay part arrival for RO-101 task to tick 160
        target_task_id = "TASK-101-1"
        for p in snap.part_requirements:
            if p.task_id == target_task_id:
                p.usable_ready_tick = 160

        scheduler = T1BitsetScheduler()
        result = scheduler.schedule(snap)

        assignment = next((a for a in result.plan.assignments if a.task_id == target_task_id), None)
        if assignment is not None:
            assert assignment.start_tick >= 160

    def test_c3_precedence_dag_enforcement(self, validated_snapshot: DealershipSnapshotSchema):
        """Successor task must strictly start at or after predecessor end_tick."""
        scheduler = T1BitsetScheduler()
        result = scheduler.schedule(validated_snapshot)

        assignment_map = {a.task_id: a for a in result.plan.assignments}
        for task in validated_snapshot.tasks:
            if task.task_id in assignment_map:
                succ_a = assignment_map[task.task_id]
                for pred_id in task.predecessor_task_ids:
                    if pred_id in assignment_map:
                        pred_a = assignment_map[pred_id]
                        assert succ_a.start_tick >= pred_a.end_tick

    def test_c6_lunch_break_protection(self, validated_snapshot: DealershipSnapshotSchema):
        """No technician may be assigned a task that overlaps their lunch break."""
        scheduler = T1BitsetScheduler()
        result = scheduler.schedule(validated_snapshot)

        tech_lookup = {t.tech_id: t for t in validated_snapshot.technicians}
        for a in result.plan.assignments:
            tech = tech_lookup[a.tech_id]
            lunch_start = tech.lunch_start_tick
            lunch_end = tech.lunch_start_tick + tech.lunch_duration_ticks
            # Must not overlap [lunch_start, lunch_end)
            assert not (max(a.start_tick, lunch_start) < min(a.end_tick, lunch_end))

    def test_externally_blocked_bay_respected(self, validated_snapshot: DealershipSnapshotSchema):
        """Externally blocked bay interval must not contain any task assignments."""
        scheduler = T1BitsetScheduler()
        blocked_bay = "BAY-02"
        b_start = 100
        b_end = 124

        result = scheduler.schedule(
            validated_snapshot,
            blocked_bay_intervals=[(blocked_bay, b_start, b_end)],
        )

        for a in result.plan.assignments:
            if a.bay_id == blocked_bay:
                assert not (max(a.start_tick, b_start) < min(a.end_tick, b_end))
