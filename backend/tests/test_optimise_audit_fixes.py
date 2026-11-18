"""Systematic Regression Tests for Task 1.4 Audit Findings and Correctness Fixes.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md
"""

from decimal import Decimal
import pytest

from app.optimise import (
    BayHourShadowPriceCalculator,
    CPSATScheduler,
    CustomerAuthorizationEvidence,
    ManagerFreightApprovalEvidence,
    OptimiseConfig,
    SchedulerTier,
    ShadowPriceStatus,
    SolverStatus,
    SupplementalAuditOracle,
    T1BitsetScheduler,
    TaskExecutionProgressEvidence,
    TechnicianFairnessEvidence,
    VehiclePhysicalEvidence,
    WorkshopEvidenceBundle,
)
from app.schemas.domain import DealershipSnapshotSchema, TaskStatus, VehiclePhysicalState
from tests.optimise_test_utils import make_synthetic_evidence


class TestC7AuthorizationsAndApprovals:
    """Verifies that no fabricated customer or manager approvals exist in the engine."""

    def test_missing_customer_auth_blocks_task(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = WorkshopEvidenceBundle(current_tick=96)  # No authorizations
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        assert len(res.plan.assignments) == 0
        for t in validated_snapshot.tasks:
            if t.status != TaskStatus.COMPLETED:
                assert "UNAUTHORIZED_CUSTOMER_ESTIMATE" in res.unscheduled_tasks[t.task_id]

    def test_false_customer_auth_blocks_task(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = WorkshopEvidenceBundle(
            current_tick=96,
            customer_authorizations={
                "RO-101": CustomerAuthorizationEvidence(ro_id="RO-101", is_authorized=False)
            },
        )
        res = scheduler.schedule(validated_snapshot, evidence=ev)
        assert "RO-101" not in {a.ro_id for a in res.plan.assignments}

    def test_freight_surcharge_threshold_logic(self):
        ev = WorkshopEvidenceBundle(
            manager_freight_approvals={
                "OFFER-HIGH": ManagerFreightApprovalEvidence(
                    offer_id="OFFER-HIGH",
                    is_approved=True,
                    approved_amount_usd=Decimal("75.00"),
                ),
                "OFFER-REJECTED": ManagerFreightApprovalEvidence(
                    offer_id="OFFER-REJECTED",
                    is_approved=False,
                ),
            }
        )

        # <= $50 threshold is approved by default
        assert ev.is_freight_approved("OFFER-CHEAP", Decimal("37.00"), threshold_usd=Decimal("50.00")) is True
        assert ev.is_freight_approved("OFFER-CHEAP", Decimal("50.00"), threshold_usd=Decimal("50.00")) is True

        # > $50 threshold requires explicit approval
        assert ev.is_freight_approved("OFFER-HIGH", Decimal("65.00"), threshold_usd=Decimal("50.00")) is True
        assert ev.is_freight_approved("OFFER-HIGH", Decimal("80.00"), threshold_usd=Decimal("50.00")) is False  # Exceeds approved amount
        assert ev.is_freight_approved("OFFER-REJECTED", Decimal("55.00"), threshold_usd=Decimal("50.00")) is False
        assert ev.is_freight_approved("OFFER-UNLISTED", Decimal("55.00"), threshold_usd=Decimal("50.00")) is False


class TestTaskExecutionLifecycles:
    """Verifies that IN_PROGRESS and STALLED tasks require explicit remaining duration."""

    def test_in_progress_missing_duration_fails_closed(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        # Clear progress evidence for TASK-101-01 (IN_PROGRESS)
        ev.task_progress["TASK-101-01"].remaining_duration_ticks = None

        res = scheduler.schedule(validated_snapshot, evidence=ev)
        assert "TASK-101-01" in res.unscheduled_tasks
        assert "MISSING_EXECUTION_PROGRESS" in res.unscheduled_tasks["TASK-101-01"]

    def test_completed_tasks_never_scheduled(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        # TASK-104-01 is COMPLETED in S-MATH-01
        scheduled_task_ids = {a.task_id for a in res.plan.assignments}
        assert "TASK-104-01" not in scheduled_task_ids


class TestPrecedenceTransitiveClosure:
    """Verifies that any successor of an excluded predecessor cannot be scheduled."""

    def test_multilevel_chain_exclusion(self, validated_snapshot: DealershipSnapshotSchema):
        snap = validated_snapshot.model_copy(deep=True)
        # Build A -> B -> C dependency chain
        tasks_map = {t.task_id: t for t in snap.tasks}
        tasks_map["TASK-102-01"].predecessor_task_ids = ["TASK-101-01"]
        tasks_map["TASK-103-01"].predecessor_task_ids = ["TASK-102-01"]

        # Invalidate parts for TASK-101-01
        for p in snap.part_requirements:
            if p.task_id == "TASK-101-01":
                p.usable_ready_tick = None

        scheduler = T1BitsetScheduler()
        ev = make_synthetic_evidence(snap, authorize_all=True)
        res = scheduler.schedule(snap, evidence=ev)

        assert "TASK-101-01" in res.unscheduled_tasks
        assert "TASK-102-01" in res.unscheduled_tasks
        assert "TASK-103-01" in res.unscheduled_tasks
        assert "PREDECESSOR_UNSCHEDULED" in res.unscheduled_tasks["TASK-102-01"]
        assert "PREDECESSOR_UNSCHEDULED" in res.unscheduled_tasks["TASK-103-01"]


class TestVehiclePhysicalStateAndMovement:
    """Verifies physical movement, holding, and UNKNOWN state handling."""

    def test_in_holding_movement_delay_enforced(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True, current_tick=96)
        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        # Vehicles in holding lot cannot start before tick 96 + 2 = 98
        for a in res.plan.assignments:
            ro = next(r for r in validated_snapshot.repair_orders if r.ro_id == a.ro_id)
            phys_ev = ev.vehicle_evidence.get(ro.vehicle_id)
            if phys_ev and phys_ev.is_in_holding:
                assert a.start_tick >= 98

    def test_supplemental_audit_catches_unknown_state(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        ro101 = next(r for r in validated_snapshot.repair_orders if r.ro_id == "RO-101")
        ev.vehicle_evidence[ro101.vehicle_id].physical_state = VehiclePhysicalState.UNKNOWN

        oracle = SupplementalAuditOracle(validated_snapshot, ev)
        # Create a mock plan scheduling RO-101
        scheduler = T1BitsetScheduler()
        ev_valid = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        plan = scheduler.schedule(validated_snapshot, evidence=ev_valid).plan

        audit_res = oracle.audit_plan(plan)
        assert audit_res.is_valid is False
        assert any(v["code"] == "C5_UNKNOWN_STATE_MOVE" for v in audit_res.violations)


class TestC1C6SupplementalAudit:
    """Verifies vehicle lifting capacity and flat-rate fairness band compliance."""

    def test_lifting_capacity_exceeded_flagged_by_supplemental_audit(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        ro101 = next(r for r in validated_snapshot.repair_orders if r.ro_id == "RO-101")
        # Increase vehicle weight to 15,000 lbs (exceeding standard 10,000 lb bays)
        ev.vehicle_evidence[ro101.vehicle_id].vehicle_weight_lbs = 15000

        oracle = SupplementalAuditOracle(validated_snapshot, ev)
        scheduler = T1BitsetScheduler()
        ev_valid = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        plan = scheduler.schedule(validated_snapshot, evidence=ev_valid).plan

        audit_res = oracle.audit_plan(plan)
        assert audit_res.is_valid is False
        assert any(v["code"] == "C1_BAY_CAPACITY_EXCEEDED" for v in audit_res.violations)

    def test_fairness_band_exceeded_flagged(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        # TECH-03 has historical hours that severely violate the 15% band
        ev.technician_fairness["TECH-03"] = TechnicianFairnessEvidence(
            tech_id="TECH-03",
            skill_group="GENERAL",
            historical_allocated_hours=Decimal("100.0"),  # Way above peer median 40.0
            median_peer_hours=Decimal("40.0"),
        )

        oracle = SupplementalAuditOracle(validated_snapshot, ev)
        scheduler = T1BitsetScheduler()
        plan = scheduler.schedule(validated_snapshot, evidence=ev).plan

        audit_res = oracle.audit_plan(plan)
        assert audit_res.is_valid is False
        assert any("fairness band" in v["message"] for v in audit_res.violations)


class TestEconomicObjectiveAndArithmetic:
    """Verifies honest metrics calculations, churn status, and bay blocked ticks."""

    def test_churn_marked_not_applicable_without_prior_plan(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        assert res.metrics.churn_status == "NOT_APPLICABLE"
        assert res.metrics.schedule_churn_score is None
        assert res.metrics.schedule_churn_penalty_usd is None

    def test_bay_blocked_ticks_recorded(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        # RO-104 is immobilized on BAY-01 for the entire 108 ticks [96, 204]
        assert res.metrics.bay_blocked_ticks == 108
        assert res.metrics.objective_completeness == "PARTIAL_CONFIGURED"
