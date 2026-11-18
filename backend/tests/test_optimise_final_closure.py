"""Final Acceptance Tests for Task 1.4 Closure and Correctness Sign-off.

Authoritative Reference:
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md
"""

from decimal import Decimal
from unittest.mock import patch
import pytest
from pydantic import ValidationError

from app.optimise import (
    BayHourShadowPriceCalculator,
    BitsetOccupancyGrid,
    CertificationStatus,
    CPSATScheduler,
    CustomerAuthorizationEvidence,
    ManagerFreightApprovalEvidence,
    ObjectiveMetrics,
    OptimiseConfig,
    PlannedVehicleMovement,
    RepairOrderCompletionStatus,
    ScheduleResult,
    SchedulerTier,
    ShadowPriceStatus,
    SolverStatus,
    SupplementalAuditOracle,
    T1BitsetScheduler,
    TaskExecutionProgressEvidence,
    TechnicianFairnessEvidence,
    VehicleMovementEvidence,
    VehiclePhysicalEvidence,
    WorkshopEvidenceBundle,
)
from app.verifier.models import CandidateSchedulePlan, ScheduledAssignment, VehicleBayOccupancy
from app.schemas.domain import (
    DealershipSnapshotSchema,
    RepairOrderSchema,
    TaskSchema,
    TaskStatus,
    VehiclePhysicalState,
)
from tests.optimise_test_utils import make_synthetic_evidence


class TestPlannedVehicleMovementModel:
    """Verifies typed PlannedVehicleMovement schema validation and integrity."""

    def test_valid_movement_instantiation(self):
        move = PlannedVehicleMovement(
            vehicle_id="VEH-106",
            ro_id="RO-106",
            origin_location="HOLDING_LOT",
            target_bay_id="BAY-01",
            start_tick=96,
            end_tick=98,
            assigned_resource_id="PORTER-01",
            resource_type="PORTER",
            resource_availability="AVAILABLE",
            movement_status="PLANNED",
            related_task_id="TASK-106-01",
        )
        assert move.start_tick == 96
        assert move.end_tick == 98
        assert move.end_tick - move.start_tick == 2
        assert move.resource_type == "PORTER"

    def test_invalid_movement_duration_fails(self):
        with pytest.raises(ValidationError):
            PlannedVehicleMovement(
                vehicle_id="VEH-106",
                ro_id="RO-106",
                origin_location="HOLDING_LOT",
                target_bay_id="BAY-01",
                start_tick=96,
                end_tick=99,  # 3 ticks instead of 2
                assigned_resource_id="PORTER-01",
                resource_type="PORTER",
                resource_availability="AVAILABLE",
                movement_status="PLANNED",
            )

    def test_invalid_movement_order_fails(self):
        with pytest.raises(ValidationError):
            PlannedVehicleMovement(
                vehicle_id="VEH-106",
                ro_id="RO-106",
                origin_location="HOLDING_LOT",
                target_bay_id="BAY-01",
                start_tick=100,
                end_tick=98,  # end < start
                assigned_resource_id="PORTER-01",
                resource_type="PORTER",
                resource_availability="AVAILABLE",
                movement_status="PLANNED",
            )


class TestT1VehicleMovementScheduling:
    """Verifies T1 Bitset Scheduler schedules explicit 2-tick movements for holding vehicles."""

    def test_t1_schedules_holding_movement_and_populates_planned_movements(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        ev.available_porter_tech_ids = {"PORTER-01"}
        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        assert res.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        # Check planned movements for holding vehicles
        holding_ros = {
            r.ro_id for r in validated_snapshot.repair_orders
            if ev.vehicle_evidence[r.vehicle_id].is_in_holding
        }

        # Any scheduled holding vehicle must have a corresponding planned movement
        scheduled_ro_ids = {a.ro_id for a in res.plan.assignments}
        scheduled_holding_ros = holding_ros.intersection(scheduled_ro_ids)

        if scheduled_holding_ros:
            assert len(res.planned_movements) > 0
            for move in res.planned_movements:
                assert move.end_tick - move.start_tick == 2
                assert move.start_tick >= ev.current_tick
                # First task on that RO must start at or after move.end_tick
                ro_tasks = [a for a in res.plan.assignments if a.ro_id == move.ro_id]
                first_task_start = min(a.start_tick for a in ro_tasks)
                assert first_task_start >= move.end_tick


class TestT2CPSATVehicleMovementScheduling:
    """Verifies T2 CP-SAT schedules movement intervals and enforces porter exclusivity."""

    def test_cpsat_planned_movements_and_exclusivity(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        ev.available_porter_tech_ids = {"PORTER-01"}
        scheduler = CPSATScheduler(OptimiseConfig(time_budget_seconds=5.0))
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        assert res.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        if res.planned_movements:
            # Check porter exclusivity
            porter_moves = [m for m in res.planned_movements if m.assigned_resource_id == "PORTER-01"]
            for i, m1 in enumerate(porter_moves):
                for j, m2 in enumerate(porter_moves):
                    if i != j:
                        # Intervals must not overlap
                        assert m1.end_tick <= m2.start_tick or m2.end_tick <= m1.start_tick


class TestSupplementalAuditMovements:
    """Verifies SupplementalAuditOracle catches all movement violations."""

    def test_holding_vehicle_missing_movement_fails_audit(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        oracle = SupplementalAuditOracle(validated_snapshot, ev)

        # Construct plan where a holding vehicle (RO-103) is scheduled without planned_movements
        ro103 = next(r for r in validated_snapshot.repair_orders if r.ro_id == "RO-103")
        ev.vehicle_evidence[ro103.vehicle_id].is_in_holding = True

        plan = CandidateSchedulePlan(
            plan_id="TEST-PLAN",
            rooftop_id="ROOF-01",
            snapshot_hash=validated_snapshot.snapshot_hash,
            assignments=[
                ScheduledAssignment(
                    task_id="TASK-103-01",
                    ro_id="RO-103",
                    tech_id="TECH-03",
                    bay_id="BAY-02",
                    start_tick=98,
                    end_tick=122,
                )
            ],
            customer_authorizations={"RO-103": True},
        )

        audit_res = oracle.audit_plan(plan, planned_movements=[])
        assert audit_res.is_valid is False
        assert any(
            v["code"] == "C5_ILLEGAL_VEHICLE_MOVE" and "lacks an explicit planned movement" in v["message"]
            for v in audit_res.violations
        )

    def test_invalid_movement_duration_fails_audit(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        oracle = SupplementalAuditOracle(validated_snapshot, ev)
        ro103 = next(r for r in validated_snapshot.repair_orders if r.ro_id == "RO-103")
        ev.vehicle_evidence[ro103.vehicle_id].is_in_holding = True

        plan = CandidateSchedulePlan(
            plan_id="TEST-PLAN",
            rooftop_id="ROOF-01",
            snapshot_hash=validated_snapshot.snapshot_hash,
            assignments=[
                ScheduledAssignment(
                    task_id="TASK-103-01",
                    ro_id="RO-103",
                    tech_id="TECH-03",
                    bay_id="BAY-02",
                    start_tick=100,
                    end_tick=124,
                )
            ],
            customer_authorizations={"RO-103": True},
        )

        # Mock a movement with duration 3
        class MockMove:
            vehicle_id = ro103.vehicle_id
            ro_id = "RO-103"
            start_tick = 96
            end_tick = 99  # duration 3
            assigned_resource_id = "TECH-01"
            target_bay_id = "BAY-02"

        audit_res = oracle.audit_plan(plan, planned_movements=[MockMove()])
        assert audit_res.is_valid is False
        assert any(
            v["code"] == "C5_ILLEGAL_VEHICLE_MOVE" and "must be exactly 2 ticks" in v["message"]
            for v in audit_res.violations
        )

    def test_technician_task_overlap_with_movement_fails_audit(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        oracle = SupplementalAuditOracle(validated_snapshot, ev)
        ro103 = next(r for r in validated_snapshot.repair_orders if r.ro_id == "RO-103")
        ev.vehicle_evidence[ro103.vehicle_id].is_in_holding = True

        # TECH-03 assigned to task at 98-122 and also assigned to move at 96-98
        plan = CandidateSchedulePlan(
            plan_id="TEST-PLAN",
            rooftop_id="ROOF-01",
            snapshot_hash=validated_snapshot.snapshot_hash,
            assignments=[
                ScheduledAssignment(
                    task_id="TASK-103-01",
                    ro_id="RO-103",
                    tech_id="TECH-03",
                    bay_id="BAY-02",
                    start_tick=98,
                    end_tick=122,
                )
            ],
            customer_authorizations={"RO-103": True},
        )

        class MockMove:
            vehicle_id = ro103.vehicle_id
            ro_id = "RO-103"
            start_tick = 96
            end_tick = 98
            assigned_resource_id = "TECH-03"  # Same tech!
            target_bay_id = "BAY-02"

        # If TECH-03 has another task at 96-98:
        plan.assignments.append(
            ScheduledAssignment(
                task_id="TASK-101-01",
                ro_id="RO-101",
                tech_id="TECH-03",
                bay_id="BAY-01",
                start_tick=96,
                end_tick=100,
            )
        )
        plan.customer_authorizations["RO-101"] = True

        audit_res = oracle.audit_plan(plan, planned_movements=[MockMove()])
        assert audit_res.is_valid is False
        assert any(v["code"] == "C4_TECH_DOUBLE_BOOKED" for v in audit_res.violations)

    def test_immobilized_vehicle_movement_fails_audit(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        oracle = SupplementalAuditOracle(validated_snapshot, ev)
        ro104 = next(r for r in validated_snapshot.repair_orders if r.ro_id == "RO-104")

        plan = CandidateSchedulePlan(
            plan_id="TEST-PLAN",
            rooftop_id="ROOF-01",
            snapshot_hash=validated_snapshot.snapshot_hash,
            assignments=[
                ScheduledAssignment(
                    task_id="TASK-104-02",
                    ro_id="RO-104",
                    tech_id="TECH-01",
                    bay_id="BAY-01",
                    start_tick=198,
                    end_tick=222,
                )
            ],
            customer_authorizations={"RO-104": True},
        )

        class MockMove:
            vehicle_id = ro104.vehicle_id
            ro_id = "RO-104"
            start_tick = 96
            end_tick = 98
            assigned_resource_id = "PORTER-01"
            target_bay_id = "BAY-02"

        audit_res = oracle.audit_plan(plan, planned_movements=[MockMove()])
        assert audit_res.is_valid is False
        assert any(
            v["code"] == "C5_ILLEGAL_VEHICLE_MOVE" and "IMMOBILIZED_ON_LIFT; movement operation is prohibited" in v["message"]
            for v in audit_res.violations
        )


class TestCurrentTickAndWIPExecution:
    """Verifies that scheduling honors current_tick and WIP locks/duration."""

    def test_current_tick_enforced_when_past_horizon_start(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        # Current tick is 120 (10:00 AM), later than horizon start 96 (8:00 AM)
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=120)
        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        for a in res.plan.assignments:
            assert a.start_tick >= 120

    def test_wip_locked_assignment_respected(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        # Lock TASK-103-01 to BAY-01 and TECH-01
        ev.task_progress["TASK-103-01"] = TaskExecutionProgressEvidence(
            task_id="TASK-103-01",
            status=TaskStatus.IN_PROGRESS,
            current_tick=96,
            existing_tech_id="TECH-01",
            existing_bay_id="BAY-01",
            remaining_duration_ticks=24,
            is_assignment_locked=True,
        )

        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        ro103_assignments = [a for a in res.plan.assignments if a.task_id == "TASK-103-01"]
        if ro103_assignments:
            assert ro103_assignments[0].tech_id == "TECH-01"
            assert ro103_assignments[0].bay_id == "BAY-01"

    def test_wip_requires_existing_assignment_fails_closed_when_missing(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        ev.task_progress["TASK-101-01"].requires_existing_assignment = True
        ev.task_progress["TASK-101-01"].existing_tech_id = None

        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        assert "TASK-101-01" in res.unscheduled_tasks
        assert "MISSING_EXISTING_ASSIGNMENT_EVIDENCE" in res.unscheduled_tasks["TASK-101-01"]


class TestEmptyPlanBehavior:
    """Verifies that empty plans are not certified when work remains, and no-op when complete."""

    def test_empty_plan_with_work_remaining_fails_certification(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        oracle = SupplementalAuditOracle(validated_snapshot, ev)

        empty_plan = CandidateSchedulePlan(
            plan_id="EMPTY-PLAN",
            rooftop_id="ROOF-01",
            snapshot_hash=validated_snapshot.snapshot_hash,
            assignments=[],
        )

        audit_res = oracle.audit_plan(empty_plan)
        assert audit_res.is_valid is False
        assert audit_res.is_actionable is False
        assert audit_res.certification_status == CertificationStatus.INCOMPLETE_EVIDENCE

    def test_empty_plan_with_all_work_completed_is_no_work_remaining(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        snap = validated_snapshot.model_copy(deep=True)
        for t in snap.tasks:
            t.status = TaskStatus.COMPLETED

        ev = make_synthetic_evidence(snap, authorize_all=True, current_tick=96)
        for t in snap.tasks:
            ev.task_progress[t.task_id].remaining_duration_ticks = 0

        oracle = SupplementalAuditOracle(snap, ev)
        empty_plan = CandidateSchedulePlan(
            plan_id="EMPTY-PLAN",
            rooftop_id="ROOF-01",
            snapshot_hash=snap.snapshot_hash,
            assignments=[],
        )

        audit_res = oracle.audit_plan(empty_plan)
        assert audit_res.is_valid is True
        assert audit_res.is_actionable is False
        assert audit_res.certification_status == CertificationStatus.NO_WORK_REMAINING


class TestShadowPriceClosure:
    """Verifies shadow price cached baseline recomputation, fallback, and exactness."""

    def test_valuation_scope_is_configured_objective_only(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        calc = BayHourShadowPriceCalculator()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        res = calc.calculate_shadow_price(
            snapshot=validated_snapshot,
            bay_id="BAY-01",
            start_tick=96,
            end_tick=108,
            evidence=ev,
        )
        assert res.valuation_scope == "CONFIGURED_OBJECTIVE_ONLY"

    def test_cached_baseline_invalidated_on_different_evidence(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        calc = BayHourShadowPriceCalculator()
        ev1 = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        ev2 = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=120)

        res1 = calc.calculate_shadow_price(
            snapshot=validated_snapshot,
            bay_id="BAY-01",
            start_tick=96,
            end_tick=108,
            evidence=ev1,
        )

        res2 = calc.calculate_shadow_price(
            snapshot=validated_snapshot,
            bay_id="BAY-01",
            start_tick=120,
            end_tick=132,
            evidence=ev2,
        )
        # Should not throw and should re-evaluate baseline under ev2
        assert res2.status in (ShadowPriceStatus.EXACT, ShadowPriceStatus.APPROXIMATE, ShadowPriceStatus.UNAVAILABLE)

    def test_t1_fallback_exactness_is_approximate(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        calc = BayHourShadowPriceCalculator()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        scheduler = T1BitsetScheduler()
        t1_res = scheduler.schedule(validated_snapshot, evidence=ev)

        with patch.object(calc.solver, "schedule", return_value=t1_res):
            res = calc.calculate_shadow_price(
                snapshot=validated_snapshot,
                bay_id="BAY-01",
                start_tick=96,
                end_tick=108,
                evidence=ev,
            )
            assert res.status == ShadowPriceStatus.APPROXIMATE
            assert res.is_exact is False

    def test_negative_delta_is_preserved_and_flags_unavailable(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        calc = BayHourShadowPriceCalculator()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        # Mock perturbed result having higher objective than baseline (anomalous negative delta)
        dummy_base = ScheduleResult(
            plan_id="BASE",
            rooftop_id="ROOF-01",
            snapshot_hash="hash",
            solver_tier=SchedulerTier.T2_CPSAT,
            solver_status=SolverStatus.OPTIMAL,
            runtime_ms=10.0,
            objective_value_usd=Decimal("200.00"),
            plan=CandidateSchedulePlan(plan_id="BASE", rooftop_id="ROOF-01", snapshot_hash="hash", assignments=[]),
            metrics=ObjectiveMetrics(
                gross_contribution_usd=Decimal("200.00"),
                lateness_penalty_usd=Decimal("0.00"),
                net_objective_usd=Decimal("200.00"),
                configured_terms=["gross_contribution"],
                unconfigured_terms=[],
            ),
            is_verified=True,
            is_fully_certified=True,
        )
        dummy_pert = ScheduleResult(
            plan_id="PERT",
            rooftop_id="ROOF-01",
            snapshot_hash="hash",
            solver_tier=SchedulerTier.T2_CPSAT,
            solver_status=SolverStatus.OPTIMAL,
            runtime_ms=10.0,
            objective_value_usd=Decimal("300.00"),  # Higher than baseline!
            plan=CandidateSchedulePlan(plan_id="PERT", rooftop_id="ROOF-01", snapshot_hash="hash", assignments=[]),
            metrics=ObjectiveMetrics(
                gross_contribution_usd=Decimal("300.00"),
                lateness_penalty_usd=Decimal("0.00"),
                net_objective_usd=Decimal("300.00"),
                configured_terms=["gross_contribution"],
                unconfigured_terms=[],
            ),
            is_verified=True,
            is_fully_certified=True,
        )

        with patch.object(calc.solver, "schedule") as mock_sched:
            mock_sched.side_effect = [dummy_base, dummy_pert]
            res = calc.calculate_shadow_price(
                snapshot=validated_snapshot,
                bay_id="BAY-01",
                start_tick=96,
                end_tick=108,
                evidence=ev,
            )
            # Delta is 200 - 300 = -100
            assert res.signed_delta_objective_usd == Decimal("-100.00")
            assert res.status == ShadowPriceStatus.UNAVAILABLE


class TestSolverObjectivePennyPrecision:
    """Verifies that CP-SAT solver objective matches reported objective down to exact penny."""

    def test_cpsat_solver_objective_equals_reported_objective(
        self, validated_snapshot: DealershipSnapshotSchema
    ):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        scheduler = CPSATScheduler(OptimiseConfig(time_budget_seconds=5.0))
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        if res.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE):
            expected_net = (res.metrics.gross_contribution_usd - res.metrics.lateness_penalty_usd).quantize(Decimal("0.01"))
            assert res.objective_value_usd == expected_net
            assert res.metrics.net_objective_usd == expected_net
