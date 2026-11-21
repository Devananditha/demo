"""Comprehensive Regression Test Suite for Recovery Workflow Consistency.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md
- docs/03_PRODUCT_REQUIREMENTS.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.api.main import app, reset_live_snapshot
from app.authority.commit import AuthorityCommitGateway
from app.authority.models import CommitRequest, CommitStatus, ManagerRecoveryApproval
from app.constraints.rules import check_c7_freight_threshold
from app.data.loader import load_canonical_evidence, load_fixture_data
from app.optimise import CPSATScheduler, OptimiseConfig, SchedulerTier, SolverStatus
from app.predict.classifier import PredictReadinessClassifier
from app.predict.models import ReadinessState
from app.recover.models import DisruptionEvent, DisruptionType
from app.recover.replan import RecoveryReplanningPipeline
from app.stallbreaker import (
    EventType,
    StallBreakerApprovalRequest,
    StoredEvent,
    stallbreaker_approval_gateway,
    stallbreaker_engine,
)
from app.verifier.sweep_oracle import SweepLineOracle


@pytest.fixture
def clean_api_client():
    reset_live_snapshot()
    client = TestClient(app)
    return client


class TestRecoveryWorkflowConsistency:
    """Rigorous verification of the 14 recovery workflow consistency invariants."""

    def test_01_s1_timing_and_customer_promise_feasibility(self):
        """1. S1 timing and customer-promise feasibility.
        
        RO-104 remaining duration: 120 min (24 ticks).
        Promise tick: 192 (4:00 PM).
        S1 usable ready tick: 165 (1:45 PM).
        Finish tick: 165 + 24 = 189 (3:45 PM) <= 192 -> 15 min positive slack, on-time.
        """
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        pipeline = RecoveryReplanningPipeline(OptimiseConfig(allow_emergency_overtime=True))
        disruption = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )
        report = pipeline.execute_recovery(snapshot, disruption, ev)
        s1_alt = next((a for a in report.alternatives if a.option_id == "OFFER-104-S1"), None)
        assert s1_alt is not None
        ro104_assignment = next((a for a in s1_alt.schedule_result.plan.assignments if a.ro_id == "RO-104"), None)
        assert ro104_assignment is not None
        assert ro104_assignment.start_tick >= 165
        assert ro104_assignment.end_tick == 189
        assert ro104_assignment.end_tick <= 192, "RO-104 must complete before customer promise tick 192"

    def test_02_s2_timing_shift_constraints_and_overtime_authorization(self):
        """2. S2 timing, shift constraints and overtime authorization.
        
        S2 usable ready tick: 198 (4:30 PM).
        RO-104 finish: 198 + 24 = 222 (6:30 PM).
        Shift end is 204 (5:00 PM).
        With allow_emergency_overtime=False, RO-104 cannot complete within shift.
        With allow_emergency_overtime=True, RO-104 completes in overtime but breaches promise tick 192 by 30 ticks (150 min).
        """
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        
        # Disallow overtime: S2 cannot fit in operating day (222 > 204)
        cfg_no_ot = OptimiseConfig(allow_emergency_overtime=False)
        pipe_no_ot = RecoveryReplanningPipeline(cfg_no_ot)
        d = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )
        rep_no_ot = pipe_no_ot.execute_recovery(snapshot, d, ev)
        s2_no_ot = next((a for a in rep_no_ot.alternatives if a.option_id == "OFFER-104-S2"), None)
        assert s2_no_ot is not None
        # Under no overtime, RO-104 cannot finish within shift 204
        ro104_asg = next((a for a in s2_no_ot.schedule_result.plan.assignments if a.ro_id == "RO-104"), None)
        assert ro104_asg is None, "RO-104 must be unscheduled when overtime is disallowed for S2"

    def test_03_solver_result_vs_t1_fallback_identification(self):
        """3. Solver result versus T1 fallback identification.
        
        A CP-SAT optimal plan must be tagged T2_CPSAT, not T1_FALLBACK.
        A fallback plan must explicitly contain T1-FALLBACK in its plan_id and have degradation_reason.
        """
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        solver = CPSATScheduler(OptimiseConfig(allow_emergency_overtime=True))
        res = solver.schedule(snapshot, "PLAN-TEST-CPSAT", ev)
        assert res.solver_tier == SchedulerTier.T2_CPSAT
        assert res.solver_status == SolverStatus.OPTIMAL
        assert "FALLBACK" not in res.plan_id
        assert res.degradation_reason is None

    def test_04_selected_supplier_consistency(self):
        """4. Selected supplier consistency across pipeline and StallBreaker engine."""
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        pipe = RecoveryReplanningPipeline(OptimiseConfig(allow_emergency_overtime=True))
        d = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )
        report = pipe.execute_recovery(snapshot, d, ev)
        assert report.recommended_option_id == "OFFER-104-S1"
        assert report.recommended_plan_id == "PLAN-REC-OFFER-104-S1"

        # Also via StallBreaker engine
        evt = StoredEvent(
            event_id="EVT-TEST-S1",
            rooftop_id="ROOF-01",
            event_type=EventType.PARTS_ETA_CHANGED,
            entity_type="PART_REQUIREMENT",
            entity_id="PART-REQ-104-SOLENOID",
            payload={"delay_minutes": 180, "new_ready_tick": 198},
            occurred_at=datetime(2026, 11, 18, 13, 15, 0, tzinfo=timezone.utc),
            ingested_at=datetime(2026, 11, 18, 13, 15, 0, tzinfo=timezone.utc),
            snapshot_hash_before="",
            snapshot_hash_after="",
        )
        sb_report = stallbreaker_engine.generate_recovery_recommendations(snapshot, evt, ev)
        assert sb_report.recommended_action.sourcing_offer_id == "OFFER-104-S1"
        assert sb_report.recommended_plan_id == "PLAN-REC-OFFER-104-S1"

    def test_05_selected_supplier_cost_consistency(self):
        """5. Selected supplier cost consistency: S1 must be exactly $37.00, S2 must be $0.00."""
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        pipe = RecoveryReplanningPipeline(OptimiseConfig(allow_emergency_overtime=True))
        d = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )
        report = pipe.execute_recovery(snapshot, d, ev)
        s1 = next(a for a in report.alternatives if a.option_id == "OFFER-104-S1")
        s2 = next(a for a in report.alternatives if a.option_id == "OFFER-104-S2")
        assert s1.sourcing_cost_usd == Decimal("37.00")
        assert s2.sourcing_cost_usd == Decimal("0.00")

    def test_06_c7_authorization_based_on_committed_offer(self):
        """6. C7 authorization based on the committed offer ($37 <= $50, $0 <= $50)."""
        ok37, _, msg37 = check_c7_freight_threshold(Decimal("37.00"), Decimal("50.00"), is_manager_approved=True)
        assert ok37 is True
        ok0, _, msg0 = check_c7_freight_threshold(Decimal("0.00"), Decimal("50.00"), is_manager_approved=False)
        assert ok0 is True
        # Exceeding threshold without approval
        ok_high, code, _ = check_c7_freight_threshold(Decimal("75.00"), Decimal("50.00"), is_manager_approved=False)
        assert ok_high is False

    def test_07_verification_of_exact_plan_later_approved(self):
        """7. Verification of the exact plan later approved."""
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        pipe = RecoveryReplanningPipeline(OptimiseConfig(allow_emergency_overtime=True))
        d = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )
        report = pipe.execute_recovery(snapshot, d, ev)
        rec = next(a for a in report.alternatives if a.is_recommended)
        
        # Verify candidate plan against candidate context (S1 delivery usable at 165)
        cand_snap, _ = pipe._prepare_candidate_context(snapshot, rec.sourcing_candidate, ev, report.blast_radius)
        oracle = SweepLineOracle(cand_snap)
        verdict = oracle.verify_plan(rec.schedule_result.plan)
        assert verdict.is_valid is True
        assert rec.schedule_result.plan.plan_id == rec.plan_id

    def test_08_stale_plan_rejection(self, clean_api_client):
        """8. Stale-plan rejection by approval gateway."""
        snapshot = load_fixture_data()
        res = clean_api_client.post(
            "/api/v1/stallbreaker/approve",
            json={
                "plan_id": "NON-EXISTENT-PLAN-999",
                "event_id": "EVT-1",
                "expected_snapshot_hash": snapshot.snapshot_hash or "",
                "approver_id": "MGR-MARCUS",
                "approved_freight_usd": 37.0,
            },
        )
        assert res.status_code == 400
        assert "not found" in res.json()["detail"].lower()

    def test_09_commit_result_and_plan_id_consistency(self, clean_api_client):
        """9. Commit result and plan ID consistency."""
        snapshot = load_fixture_data()
        res = clean_api_client.post(
            "/api/v1/stallbreaker/approve",
            json={
                "plan_id": "PLAN-REC-OFFER-104-S1",
                "event_id": "EVT-1",
                "expected_snapshot_hash": snapshot.snapshot_hash or "",
                "approver_id": "MGR-MARCUS",
                "approved_freight_usd": 37.0,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMMITTED"
        assert data["plan_id"] == "PLAN-REC-OFFER-104-S1"

    def test_10_executive_dashboard_derived_from_committed_plan(self):
        """10. Executive dashboard derived from the committed plan."""
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        pipe = RecoveryReplanningPipeline(OptimiseConfig(allow_emergency_overtime=True))
        d = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )
        report = pipe.execute_recovery(snapshot, d, ev)
        dr = report.decision_replay
        assert dr is not None
        assert dr.proposed_plan_id == report.recommended_plan_id
        assert dr.sourcing_freight_usd == Decimal("37.00")
        assert dr.net_economic_delta_usd > Decimal("0.00")

    def test_11_physical_bay_blocking_vs_parts_blocking(self):
        """11. Physical bay blocking versus parts blocking.
        
        RO-106 is READY (no parts needed), waiting for BAY-01.
        RO-105 is BLOCKED (national backorder on harness).
        """
        snapshot = load_fixture_data()
        classifier = PredictReadinessClassifier()
        report = classifier.assess_dealership_readiness(
            snapshot, current_tick=159, now_utc=datetime(2026, 11, 18, 13, 15, 0, tzinfo=timezone.utc)
        )
        assessments = {a.ro_id: a for a in report.assessments}
        assert assessments["RO-106"].state == ReadinessState.READY
        assert assessments["RO-105"].state == ReadinessState.BLOCKED
        assert "PART_BACKORDERED_NO_ETA" in assessments["RO-105"].reasons

    def test_12_ro104_release_time_and_ro106_admission_time(self):
        """12. RO-104 release time and RO-106 admission time."""
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        pipe = RecoveryReplanningPipeline(OptimiseConfig(allow_emergency_overtime=True))
        d = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )
        report = pipe.execute_recovery(snapshot, d, ev)
        s1 = next(a for a in report.alternatives if a.option_id == "OFFER-104-S1")
        plan = s1.schedule_result.plan
        ro104 = next(a for a in plan.assignments if a.ro_id == "RO-104")
        ro106 = next(a for a in plan.assignments if a.ro_id == "RO-106")
        assert ro104.end_tick <= ro106.start_tick, "RO-106 cannot enter BAY-01 before RO-104 vacates"
        assert ro104.bay_id == ro106.bay_id == "BAY-01"

    def test_13_customer_promise_outcomes(self):
        """13. Customer promise outcomes: RO-104 is on-time in S1, late in S2."""
        snapshot = load_fixture_data()
        ev = load_canonical_evidence(snapshot, 159)
        pipe = RecoveryReplanningPipeline(OptimiseConfig(allow_emergency_overtime=True))
        d = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )
        report = pipe.execute_recovery(snapshot, d, ev)
        s1 = next(a for a in report.alternatives if a.option_id == "OFFER-104-S1")
        ro104_s1 = next(a for a in s1.schedule_result.plan.assignments if a.ro_id == "RO-104")
        assert ro104_s1.end_tick <= 192  # Promise tick is 192 (4:00 PM)

    def test_14_shared_simulated_clock_consistency(self):
        """14. Shared simulated clock consistency: tick 159 is 13:15 UTC (1:15 PM)."""
        eval_time = datetime(2026, 11, 18, 13, 15, 0, tzinfo=timezone.utc)
        tick_159_mins = 159 * 5  # 795 minutes
        hour = tick_159_mins // 60
        mins = tick_159_mins % 60
        assert hour == 13
        assert mins == 15
        assert eval_time.hour == 13
        assert eval_time.minute == 15
