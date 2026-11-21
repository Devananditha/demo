"""Comprehensive Test Suite for ServiceYield AI Economic Decision & Optimisation Engine.

Verifies:
1. Shared dealership state and EconomicParametersSchema validation.
2. CP-SAT multi-operation, multi-bay scheduling under hard constraints C1–C7.
3. Multi-term economic objective: gross contribution, weighted lateness, bay opportunity cost, schedule churn.
4. Bay-Hour Shadow Pricing nu_b(t) discrete sensitivity estimation.
5. Independent L4 Sweep-Line Oracle verification without trusting CP-SAT status.
6. Decision Replay foundation: contribution delta, lateness delta, bay utilization, idle time, churn, and violations.
7. Decision explainability: recommendation summary, primary driver, C1–C7 itemization, objective breakdown, alternatives rejected.
8. FastAPI endpoints: /optimise/schedule, /optimise/shadow-price, /recover/replan, /verifier/verify, /replay/records, /authority/commit.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.api.main import REFERENCE_CURRENT_TICK, app
from app.data.loader import load_canonical_evidence, load_fixture_data
from app.optimise.config import OptimiseConfig
from app.optimise.cpsat_solver import CPSATScheduler
from app.optimise.models import SchedulerTier, ShadowPriceStatus, SolverStatus
from app.optimise.shadow_price import BayHourShadowPriceCalculator
from app.recover.models import DisruptionEvent, DisruptionType
from app.recover.replan import RecoveryReplanningPipeline
from app.replay.engine import DecisionReplayEngine, replay_engine
from app.replay.models import DecisionExplainability, DecisionReplayDiff
from app.schemas.domain import DealershipSnapshotSchema, EconomicParametersSchema
from app.verifier.sweep_oracle import SweepLineOracle
from tests.test_optimise_audit_fixes import make_synthetic_evidence


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def canonical_snapshot() -> DealershipSnapshotSchema:
    return load_fixture_data()


# ============================================================================
# 1. SHARED DEALERSHIP STATE & ECONOMIC PARAMETERS
# ============================================================================

class TestSharedStateAndEconomicParameters:
    """Verifies typed models representing shared dealership state and economic configuration."""

    def test_economic_parameters_default_values(self):
        params = EconomicParametersSchema()
        assert params.labor_contribution_per_hour_usd == Decimal("120.00")
        assert params.lateness_penalty_per_minute_usd == Decimal("0.50")
        assert params.blocked_bay_penalty_per_minute_usd == Decimal("0.00")
        assert params.churn_penalty_per_move_usd == Decimal("0.00")
        assert params.freight_approval_threshold_usd == Decimal("50.00")

    def test_economic_parameters_custom_overrides(self):
        params = EconomicParametersSchema(
            labor_contribution_per_hour_usd=Decimal("150.00"),
            lateness_penalty_per_minute_usd=Decimal("0.75"),
            blocked_bay_penalty_per_minute_usd=Decimal("1.50"),
            churn_penalty_per_move_usd=Decimal("25.00"),
            freight_approval_threshold_usd=Decimal("75.00"),
        )
        assert params.labor_contribution_per_hour_usd == Decimal("150.00")
        assert params.blocked_bay_penalty_per_minute_usd == Decimal("1.50")

    def test_optimise_config_from_economic_parameters(self):
        params = EconomicParametersSchema(
            labor_contribution_per_hour_usd=Decimal("130.00"),
            lateness_penalty_per_minute_usd=Decimal("0.60"),
            blocked_bay_penalty_per_minute_usd=Decimal("2.00"),
            churn_penalty_per_move_usd=Decimal("15.00"),
            freight_approval_threshold_usd=Decimal("60.00"),
        )
        config = OptimiseConfig.from_economic_parameters(
            params,
            allow_emergency_overtime=True,
            time_budget_seconds=5.0,
        )
        assert config.labor_contribution_per_hour_usd == Decimal("130.00")
        assert config.lateness_penalty_per_minute_usd == Decimal("0.60")
        assert config.blocked_bay_penalty_per_minute_usd == Decimal("2.00")
        assert config.churn_penalty_per_move_usd == Decimal("15.00")
        assert config.allow_emergency_overtime is True
        assert config.time_budget_seconds == 5.0

    def test_snapshot_with_economic_parameters(self, canonical_snapshot: DealershipSnapshotSchema):
        params = EconomicParametersSchema(labor_contribution_per_hour_usd=Decimal("140.00"))
        snap_copy = canonical_snapshot.model_copy(update={"economic_parameters": params})
        assert snap_copy.economic_parameters is not None
        assert snap_copy.economic_parameters.labor_contribution_per_hour_usd == Decimal("140.00")


# ============================================================================
# 2. CP-SAT OPTIMISATION ENGINE & MULTI-TERM OBJECTIVE
# ============================================================================

class TestCPSATMultiTermEconomicObjective:
    """Verifies CP-SAT scheduler multi-term economic objective and hard constraint enforcement."""

    def test_deterministic_cpsat_solver_baseline(self, canonical_snapshot: DealershipSnapshotSchema):
        config = OptimiseConfig(allow_emergency_overtime=True)
        scheduler = CPSATScheduler(config=config)
        ev = load_canonical_evidence(canonical_snapshot, current_tick=REFERENCE_CURRENT_TICK)
        result = scheduler.schedule(canonical_snapshot, plan_id="PLAN-TEST-BASELINE", evidence=ev)

        assert result.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.solver_tier == SchedulerTier.T2_CPSAT
        assert result.is_verified is True
        assert result.is_fully_certified is True
        assert len(result.plan.assignments) > 0
        assert result.metrics.gross_contribution_usd > Decimal("0.00")
        assert "gross_contribution" in result.metrics.configured_terms
        assert "lateness_penalty" in result.metrics.configured_terms

    def test_cpsat_solver_with_bay_opportunity_cost(self, canonical_snapshot: DealershipSnapshotSchema):
        # Configure positive blocked bay penalty
        config = OptimiseConfig(
            allow_emergency_overtime=True,
            blocked_bay_penalty_per_minute_usd=Decimal("1.00"),
        )
        scheduler = CPSATScheduler(config=config)
        ev = load_canonical_evidence(canonical_snapshot, current_tick=REFERENCE_CURRENT_TICK)
        result = scheduler.schedule(canonical_snapshot, plan_id="PLAN-TEST-OPP-COST", evidence=ev)

        assert result.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert "bay_blocked_penalty" in result.metrics.configured_terms
        assert result.metrics.bay_blocked_ticks >= 0
        if result.metrics.bay_blocked_ticks > 0:
            assert result.metrics.bay_blocked_penalty_usd > Decimal("0.00")

    def test_cpsat_solver_enforces_lift_immobility_c5(self, canonical_snapshot: DealershipSnapshotSchema):
        config = OptimiseConfig(allow_emergency_overtime=True)
        scheduler = CPSATScheduler(config=config)
        ev = load_canonical_evidence(canonical_snapshot, current_tick=REFERENCE_CURRENT_TICK)
        result = scheduler.schedule(canonical_snapshot, plan_id="PLAN-TEST-IMMOBILITY", evidence=ev)

        # RO-104 is IMMOBILIZED_ON_LIFT in BAY-01
        for occ in result.plan.vehicle_occupancies:
            if occ.ro_id == "RO-104":
                assert occ.bay_id == "BAY-01"


# ============================================================================
# 3. BAY-HOUR SHADOW PRICING SENSITIVITY
# ============================================================================

class TestBayHourShadowPricingSensitivity:
    """Verifies marginal value estimation nu_b(t) through discrete sensitivity re-solves."""

    def test_calculate_shadow_price_bay01(self, canonical_snapshot: DealershipSnapshotSchema):
        config = OptimiseConfig(allow_emergency_overtime=True)
        calc = BayHourShadowPriceCalculator(config=config)
        ev = load_canonical_evidence(canonical_snapshot, current_tick=159)

        # Evaluate 1-hour window on BAY-01 starting at tick 159 (1:15 PM to 2:15 PM)
        shadow_price = calc.calculate_shadow_price(
            snapshot=canonical_snapshot,
            bay_id="BAY-01",
            start_tick=159,
            end_tick=171,
            evidence=ev,
        )

        assert shadow_price.rooftop_id == canonical_snapshot.rooftop.rooftop_id
        assert shadow_price.bay_id == "BAY-01"
        assert shadow_price.interval_start_tick == 159
        assert shadow_price.interval_end_tick == 171
        assert shadow_price.duration_hours == Decimal("1.0000")
        assert shadow_price.status in (ShadowPriceStatus.EXACT, ShadowPriceStatus.APPROXIMATE)
        assert shadow_price.delta_objective_usd >= Decimal("0.00")
        assert shadow_price.shadow_price_usd_per_hour >= Decimal("0.00")

    def test_shadow_price_invalid_interval_rejected(self, canonical_snapshot: DealershipSnapshotSchema):
        calc = BayHourShadowPriceCalculator()
        with pytest.raises(ValueError, match="Invalid evaluation interval"):
            calc.calculate_shadow_price(canonical_snapshot, "BAY-01", start_tick=180, end_tick=170)


# ============================================================================
# 4. DECISION REPLAY FOUNDATION & EXPLAINABILITY
# ============================================================================

class TestDecisionReplayAndExplainability:
    """Verifies schedule difference calculations, explainability, and replay persistence."""

    def test_decision_replay_diff_calculation(self, canonical_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(canonical_snapshot, authorize_all=True)
        config = OptimiseConfig(allow_emergency_overtime=True)
        pipeline = RecoveryReplanningPipeline(config=config)

        disruption = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )

        report = pipeline.execute_recovery(
            snapshot=canonical_snapshot,
            disruption_event=disruption,
            evidence=ev,
            evaluation_time_utc=datetime(2026, 11, 18, 13, 15, tzinfo=timezone.utc),
        )

        assert report.decision_replay is not None
        diff = report.decision_replay

        # Check observables
        assert diff.baseline_plan_id == report.baseline_plan_id
        assert diff.proposed_plan_id == report.recommended_plan_id
        assert diff.delta_gross_contribution_usd >= Decimal("0.00")
        # Proposed weighted lateness should improve (decrease) relative to unmitigated baseline
        assert diff.delta_weighted_lateness_ticks <= 0
        assert diff.sourcing_freight_usd == Decimal("37.00")
        assert diff.net_economic_delta_usd > Decimal("0.00")
        assert diff.baseline_bay_utilization_pct >= 0.0
        assert diff.proposed_bay_utilization_pct >= 0.0
        assert diff.is_verified is True
        assert diff.is_fully_certified is True

    def test_decision_explainability_structure(self, canonical_snapshot: DealershipSnapshotSchema):
        ev = make_synthetic_evidence(canonical_snapshot, authorize_all=True)
        config = OptimiseConfig(allow_emergency_overtime=True)
        pipeline = RecoveryReplanningPipeline(config=config)

        disruption = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            primary_supplier_delay_minutes=180,
            delayed_ready_tick=198,
        )

        report = pipeline.execute_recovery(
            snapshot=canonical_snapshot,
            disruption_event=disruption,
            evidence=ev,
        )

        assert report.explainability is not None
        exp = report.explainability

        assert "RO-104" in exp.recommendation_summary
        assert len(exp.primary_driver) > 0

        # All C1-C7 constraints represented
        constraint_codes = [c["constraint"] for c in exp.constraints_considered]
        for expected in ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]:
            assert expected in constraint_codes

        # Objective breakdown
        assert "Gross Labor Contribution" in exp.objective_breakdown
        assert "Expedited Freight Surcharge" in exp.objective_breakdown
        assert "Net Economic Recovery Delta" in exp.objective_breakdown

        # Rejected alternatives include S2 Ground Shuttle
        rejected_options = [r["option_id"] for r in exp.alternatives_rejected]
        assert any("S2" in opt or "OFFER" in opt for opt in rejected_options)

    def test_decision_replay_ledger_persistence(self):
        engine = DecisionReplayEngine()
        diff = DecisionReplayDiff(
            baseline_plan_id="BASE-01",
            proposed_plan_id="PROP-01",
            baseline_gross_contribution_usd=Decimal("1000.00"),
            proposed_gross_contribution_usd=Decimal("1240.00"),
            delta_gross_contribution_usd=Decimal("240.00"),
            sourcing_freight_usd=Decimal("37.00"),
            rescheduling_churn_cost_usd=Decimal("0.00"),
            baseline_net_objective_usd=Decimal("775.00"),
            proposed_net_objective_usd=Decimal("1075.50"),
            net_economic_delta_usd=Decimal("300.50"),
            baseline_weighted_lateness_ticks=90,
            proposed_weighted_lateness_ticks=51,
            delta_weighted_lateness_ticks=-39,
            baseline_bay_utilization_pct=45.0,
            proposed_bay_utilization_pct=65.0,
            delta_bay_utilization_pct=20.0,
            baseline_idle_minutes=120,
            proposed_idle_minutes=30,
            delta_idle_minutes=-90,
            baseline_constraint_violations=0,
            proposed_constraint_violations=0,
            is_verified=True,
            is_fully_certified=True,
        )
        explainability = DecisionExplainability(
            recommendation_summary="Test Summary",
            primary_driver="Test Driver",
        )

        rec = engine.record_decision(
            rooftop_id="ROOF-01",
            snapshot_hash="HASH-12345",
            diff=diff,
            explainability=explainability,
        )
        assert rec.replay_id.startswith("REPLAY-")

        retrieved = engine.get_record(rec.replay_id)
        assert retrieved is not None
        assert retrieved.replay_id == rec.replay_id
        assert retrieved.diff.delta_gross_contribution_usd == Decimal("240.00")

        all_records = engine.list_records()
        assert len(all_records) >= 1


# ============================================================================
# 5. FASTAPI REST API INTEGRATION
# ============================================================================

class TestFastAPIEconomicEndpoints:
    """Verifies REST endpoints for optimization, shadow pricing, recovery, and verification."""

    def test_api_optimise_schedule_success(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        resp = client.post(
            "/api/v1/optimise/schedule",
            json={
                "rooftop_id": canonical_snapshot.rooftop.rooftop_id,
                "snapshot_hash": canonical_snapshot.snapshot_hash,
                "allow_emergency_overtime": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["solver_status"] in ("OPTIMAL", "FEASIBLE")
        assert len(data["plan"]["assignments"]) > 0
        assert data["is_verified"] is True
        assert data["is_fully_certified"] is True
        assert data["metrics"]["gross_contribution_usd"] is not None

    def test_api_optimise_shadow_price_success(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        resp = client.post(
            "/api/v1/optimise/shadow-price",
            json={
                "rooftop_id": canonical_snapshot.rooftop.rooftop_id,
                "snapshot_hash": canonical_snapshot.snapshot_hash,
                "bay_id": "BAY-01",
                "start_tick": 159,
                "end_tick": 171,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bay_id"] == "BAY-01"
        assert data["status"] in ("EXACT", "APPROXIMATE")
        assert float(data["shadow_price_usd_per_hour"]) >= 0.0

    def test_api_recover_replan_success(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        resp = client.post(
            "/api/v1/recover/replan",
            json={
                "rooftop_id": canonical_snapshot.rooftop.rooftop_id,
                "snapshot_hash": canonical_snapshot.snapshot_hash,
                "disrupted_ro_id": "RO-104",
                "disrupted_part_req_id": "PART-REQ-104-SOLENOID",
                "trigger_tick": 159,
                "primary_supplier_delay_minutes": 180,
                "allow_emergency_overtime": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended_option_id"] == "OFFER-104-S1"
        assert len(data["alternatives"]) >= 1
        assert data["decision_replay"] is not None
        assert data["decision_replay"]["sourcing_freight_usd"] == "37.00"
        assert data["explainability"] is not None
        assert "RO-104" in data["explainability"]["recommendation_summary"]

    def test_api_verifier_verify_success(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        # First generate a valid schedule plan
        sched_resp = client.post(
            "/api/v1/optimise/schedule",
            json={
                "rooftop_id": canonical_snapshot.rooftop.rooftop_id,
                "snapshot_hash": canonical_snapshot.snapshot_hash,
                "allow_emergency_overtime": True,
            },
        )
        assert sched_resp.status_code == 200
        plan = sched_resp.json()["plan"]

        # Directly audit the plan via verifier endpoint
        verify_resp = client.post(
            "/api/v1/verifier/verify",
            json={
                "rooftop_id": canonical_snapshot.rooftop.rooftop_id,
                "snapshot_hash": canonical_snapshot.snapshot_hash,
                "plan": plan,
            },
        )
        assert verify_resp.status_code == 200
        data = verify_resp.json()
        assert data["is_valid"] is True
        assert len(data["violations"]) == 0

    def test_api_replay_records_list(self, client: TestClient):
        resp = client.get("/api/v1/replay/records")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_api_authority_commit_success(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        resp = client.post(
            "/api/v1/authority/commit",
            json={
                "plan_id": "PLAN-REC-OFFER-104-S1",
                "expected_snapshot_hash": canonical_snapshot.snapshot_hash,
                "approver_id": "MGR-MARCUS",
                "approved_freight_usd": "50.00",
                "approval_notes": "Authorized expedited hotshot courier ($37.00) under C7 threshold",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMMITTED"
        assert data["outbox_events_dispatched"] > 0

    def test_api_stale_hash_rejected_409(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        resp = client.post(
            "/api/v1/optimise/schedule",
            json={
                "rooftop_id": canonical_snapshot.rooftop.rooftop_id,
                "snapshot_hash": "STALE-HASH-INCORRECT",
            },
        )
        assert resp.status_code == 409
        assert "Stale snapshot hash" in resp.json()["detail"]

    def test_api_unknown_rooftop_rejected_404(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        resp = client.post(
            "/api/v1/optimise/schedule",
            json={
                "rooftop_id": "NON-EXISTENT-ROOFTOP",
                "snapshot_hash": canonical_snapshot.snapshot_hash,
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]
