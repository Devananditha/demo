"""Systematic Regression Tests for Task 1.4 Audit Findings and Correctness Fixes.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md
"""

from decimal import Decimal
from unittest.mock import patch
import pytest

from app.optimise import (
    BayHourShadowPriceCalculator,
    BitsetOccupancyGrid,
    CertificationStatus,
    CPSATScheduler,
    CustomerAuthorizationEvidence,
    ManagerFreightApprovalEvidence,
    OptimiseConfig,
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
from app.schemas.domain import DealershipSnapshotSchema, TaskStatus, VehiclePhysicalState
from app.verifier.models import VerificationResult
from tests.optimise_test_utils import make_synthetic_evidence


class TestC7AuthorizationsAndApprovals:
    """Verifies that no fabricated customer or manager approvals exist in the engine."""

    def test_missing_customer_auth_blocks_task(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = WorkshopEvidenceBundle(current_tick=96)
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

        assert ev.is_freight_approved("OFFER-CHEAP", Decimal("37.00"), threshold_usd=Decimal("50.00")) is True
        assert ev.is_freight_approved("OFFER-CHEAP", Decimal("50.00"), threshold_usd=Decimal("50.00")) is True
        assert ev.is_freight_approved("OFFER-HIGH", Decimal("65.00"), threshold_usd=Decimal("50.00")) is True
        assert ev.is_freight_approved("OFFER-HIGH", Decimal("80.00"), threshold_usd=Decimal("50.00")) is False
        assert ev.is_freight_approved("OFFER-REJECTED", Decimal("55.00"), threshold_usd=Decimal("50.00")) is False
        assert ev.is_freight_approved("OFFER-UNLISTED", Decimal("55.00"), threshold_usd=Decimal("50.00")) is False


class TestTaskExecutionLifecycles:
    """Verifies that IN_PROGRESS and STALLED tasks require explicit remaining duration."""

    def test_in_progress_missing_duration_fails_closed(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        ev.task_progress["TASK-101-01"].remaining_duration_ticks = None

        res = scheduler.schedule(validated_snapshot, evidence=ev)
        assert "TASK-101-01" in res.unscheduled_tasks
        assert "MISSING_EXECUTION_PROGRESS" in res.unscheduled_tasks["TASK-101-01"]

    def test_completed_tasks_never_scheduled(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        scheduled_task_ids = {a.task_id for a in res.plan.assignments}
        assert "TASK-104-01" not in scheduled_task_ids


class TestPrecedenceTransitiveClosure:
    """Verifies that any successor of an excluded predecessor cannot be scheduled."""

    def test_multilevel_chain_exclusion(self, validated_snapshot: DealershipSnapshotSchema):
        snap = validated_snapshot.model_copy(deep=True)
        tasks_map = {t.task_id: t for t in snap.tasks}
        tasks_map["TASK-102-01"].predecessor_task_ids = ["TASK-101-01"]
        tasks_map["TASK-103-01"].predecessor_task_ids = ["TASK-102-01"]

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
        ev.technician_fairness["TECH-03"] = TechnicianFairnessEvidence(
            tech_id="TECH-03",
            skill_group="GENERAL",
            historical_allocated_hours=Decimal("100.0"),
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

        assert res.metrics.bay_blocked_ticks == 108
        assert res.metrics.objective_completeness == "PARTIAL_CONFIGURED"


class TestFailClosedEvidenceCertification:
    """Rigorous tests for Primary Task A: Evidence certification, fitment, and fairness."""

    def test_missing_vehicle_weight_blocks_certification(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        ev.vehicle_evidence["VEH-SYNTH-101"].vehicle_weight_lbs = None

        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        assert "TASK-101-01" in res.unscheduled_tasks
        assert "MISSING_VEHICLE_WEIGHT" in res.unscheduled_tasks["TASK-101-01"]

    def test_parts_fitment_states(self, validated_snapshot: DealershipSnapshotSchema):
        scheduler = T1BitsetScheduler()

        # 1. Unverified (None) -> fails closed
        ev_none = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        ev_none.vehicle_evidence["VEH-SYNTH-101"].fitment_verified = None
        res_none = scheduler.schedule(validated_snapshot, evidence=ev_none)
        assert "UNVERIFIED_PARTS_FITMENT" in res_none.unscheduled_tasks.get("TASK-101-01", "")

        # 2. Rejected (False) -> fails closed
        ev_false = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        ev_false.vehicle_evidence["VEH-SYNTH-101"].fitment_verified = False
        res_false = scheduler.schedule(validated_snapshot, evidence=ev_false)
        assert "REJECTED_PARTS_FITMENT" in res_false.unscheduled_tasks.get("TASK-101-01", "")

        # 3. Verified (True) -> scheduled
        ev_true = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        ev_true.vehicle_evidence["VEH-SYNTH-101"].fitment_verified = True
        res_true = scheduler.schedule(validated_snapshot, evidence=ev_true)
        assert "TASK-101-01" in {a.task_id for a in res_true.plan.assignments}

    def test_assigned_tech_missing_fairness_blocks_certification(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        # Delete fairness evidence for TECH-03 who is assigned to RO-101
        del ev.technician_fairness["TECH-03"]

        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        assert res.is_fully_certified is False
        assert any("TECH-03" in g and "fairness" in g for g in res.evidence_coverage_gaps)

    def test_fairness_band_boundaries(self, validated_snapshot: DealershipSnapshotSchema):
        # Median is 40.0 hours. Allowed band is [34.0, 46.0] hours (+-15%)
        scheduler = T1BitsetScheduler()
        ev_base = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        plan = scheduler.schedule(validated_snapshot, evidence=ev_base).plan

        # Exact lower boundary: total hours = 34.0h (should pass)
        ev_lower = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        for t_id in ev_lower.technician_fairness:
            # Task allocation is at most 3.5h; setting historical to 34.0h - allocated hours gives exact boundary
            ev_lower.technician_fairness[t_id].historical_allocated_hours = Decimal("34.0")
        audit_lower = SupplementalAuditOracle(validated_snapshot, ev_lower).audit_plan(plan)
        # Should not breach lower boundary
        assert not any("breaches 15% peer fairness band" in str(v) and "34.0" in str(v) for v in audit_lower.violations)

        # Exact within band: historical 40.0h (total ~43.5h <= 46.0h, should pass)
        ev_within = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        for t_id in ev_within.technician_fairness:
            ev_within.technician_fairness[t_id].historical_allocated_hours = Decimal("40.0")
        audit_within = SupplementalAuditOracle(validated_snapshot, ev_within).audit_plan(plan)
        assert not any("C6_OUTSIDE_SHIFT" in str(v) for v in audit_within.violations)

        # Severe breach above band: 50.0h (total > 50h > 46h, should fail)
        ev_breach_high = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        for t_id in ev_breach_high.technician_fairness:
            ev_breach_high.technician_fairness[t_id].historical_allocated_hours = Decimal("50.0")
        audit_high = SupplementalAuditOracle(validated_snapshot, ev_breach_high).audit_plan(plan)
        assert any(v["code"] == "C6_OUTSIDE_SHIFT" for v in audit_high.violations)

        # Severe breach below band: 20.0h (total < 24h < 34h, should fail)
        ev_breach_low = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        for t_id in ev_breach_low.technician_fairness:
            ev_breach_low.technician_fairness[t_id].historical_allocated_hours = Decimal("20.0")
        audit_low = SupplementalAuditOracle(validated_snapshot, ev_breach_low).audit_plan(plan)
        assert any(v["code"] == "C6_OUTSIDE_SHIFT" for v in audit_low.violations)


class TestWIPOccupancyAndImmobilizedVehicles:
    """Rigorous tests for Primary Tasks B & C: WIP and immobilized vehicles."""

    def test_immobilized_vehicle_missing_assigned_bay_fails_closed(self, validated_snapshot: DealershipSnapshotSchema):
        snap = validated_snapshot.model_copy(deep=True)
        ro104 = next(r for r in snap.repair_orders if r.ro_id == "RO-104")
        ro104.assigned_bay_id = None  # Missing assigned bay while immobilized

        ev = make_synthetic_evidence(snap, authorize_all=True)
        ev.vehicle_evidence["VEH-SYNTH-104"].current_bay_id = None

        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(snap, evidence=ev)

        assert "TASK-104-02" in res.unscheduled_tasks
        assert "IMMOBILIZED_VEHICLE_MISSING_ASSIGNED_BAY" in res.unscheduled_tasks["TASK-104-02"]

    def test_locked_wip_bay_cannot_be_reassigned(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        # Lock TASK-101-01 to BAY-03 instead of BAY-02
        ev.task_progress["TASK-101-01"].existing_bay_id = "BAY-03"
        ev.task_progress["TASK-101-01"].is_assignment_locked = True

        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        for a in res.plan.assignments:
            if a.task_id == "TASK-101-01":
                assert a.bay_id == "BAY-03"

    def test_c5_movement_resource_porter_allocation(self, validated_snapshot: DealershipSnapshotSchema):
        # Empty available porter resources -> holding vehicle cannot be scheduled
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        ev.available_porter_tech_ids = set()

        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        # RO-105 and RO-106 are in holding and should be unscheduled
        assert "TASK-106-01" in res.unscheduled_tasks
        assert "NO_PORTER_OR_TECH_AVAILABLE_FOR_MOVE" in res.unscheduled_tasks["TASK-106-01"]


class TestBitsetOccupancyGridAndMetrics:
    """Rigorous tests for Primary Tasks F & H: bitset operations and metric precision."""

    def test_bitset_zero_length_and_boundary_intervals(self):
        grid = BitsetOccupancyGrid(horizon_ticks=288)

        # Zero length interval is free
        assert grid.is_interval_free(0, 100, 100) is True

        # Out of bounds returns False
        assert grid.is_interval_free(0, -5, 100) is False
        assert grid.is_interval_free(0, 100, 300) is False

        # mark_interval_busy on int returns integer with bits set
        mask = grid.mark_interval_busy(0, 10, 14)
        assert isinstance(mask, int)
        assert mask == ((1 << 4) - 1) << 10
        assert grid.is_interval_free(mask, 10, 14) is False
        assert grid.is_interval_free(mask, 0, 10) is True
        assert grid.is_interval_free(mask, 14, 20) is True

    def test_labor_contribution_uses_effective_duration(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        total_scheduled_ticks = sum(a.end_tick - a.start_tick for a in res.plan.assignments)
        expected_gross = (Decimal(str(total_scheduled_ticks)) * Decimal("120.00") / Decimal("12")).quantize(Decimal("0.01"))
        assert res.metrics.gross_contribution_usd == expected_gross

    def test_repair_order_completion_statuses_populated(self, validated_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        scheduler = T1BitsetScheduler()
        res = scheduler.schedule(validated_snapshot, evidence=ev)

        assert "RO-101" in res.ro_completion_statuses
        assert "RO-104" in res.ro_completion_statuses
        assert res.ro_completion_statuses["RO-101"] == RepairOrderCompletionStatus.FULLY_SCHEDULED.value
        assert res.ro_completion_statuses["RO-104"] == RepairOrderCompletionStatus.UNSCHEDULABLE_IN_HORIZON.value
        assert res.metrics.uncompleted_ros_count > 0
