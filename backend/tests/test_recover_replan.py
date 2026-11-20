"""Unit and integration tests for Full-Shop Recovery Replanning Pipeline.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md (Section 2.3)
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.4)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
"""

from decimal import Decimal
import pytest

from app.optimise import OptimiseConfig, SolverStatus, WorkshopEvidenceBundle
from app.recover.models import (
    DisruptionEvent,
    DisruptionType,
    RecoveryAlternative,
    RecoveryRecommendationReport,
    SourcingCandidate,
)
from app.recover.replan import RecoveryReplanningPipeline
from app.schemas.domain import DealershipSnapshotSchema, QuoteStatus
from tests.test_optimise_audit_fixes import make_synthetic_evidence


@pytest.fixture
def disruption_event_104() -> DisruptionEvent:
    return DisruptionEvent(
        disrupted_ro_id="RO-104",
        disrupted_part_req_id="PART-REQ-104-SOLENOID",
        disruption_type=DisruptionType.PARTS_DELAY,
        trigger_tick=159,
        original_ready_tick=162,
        delayed_ready_tick=198,
        description="Supplier primary ground freight delayed 180 min",
    )


class TestRecoveryReplanningPipeline:
    """Test suite for full-shop recovery replanning, Pareto ranking, and dual certification."""

    def test_end_to_end_recovery_pipeline(
        self,
        validated_snapshot: DealershipSnapshotSchema,
        disruption_event_104: DisruptionEvent,
    ):
        """Verifies complete 10-step recovery replanning pipeline execution."""
        pipeline = RecoveryReplanningPipeline()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        report = pipeline.execute_recovery(
            snapshot=validated_snapshot,
            disruption_event=disruption_event_104,
            evidence=ev,
        )

        assert isinstance(report, RecoveryRecommendationReport)
        assert report.disruption_event.disrupted_ro_id == "RO-104"
        assert report.blast_radius.is_immobilized_on_lift is True
        assert report.blast_radius.immobilized_bay_id == "BAY-01"
        assert "RO-106" in report.blast_radius.competing_ro_ids

        # Baseline plan must exist and have unmitigated lateness
        assert report.baseline_plan_id.startswith("PLAN-BASE-")
        assert report.baseline_weighted_lateness_ticks >= 0

        # Must have evaluated alternatives
        assert len(report.alternatives) > 0
        assert len(report.pareto_frontier) > 0

        # Recommendation must be chosen from pareto frontier
        assert report.recommended_option_id is not None
        assert report.recommended_plan_id is not None
        assert any(alt.option_id == report.recommended_option_id for alt in report.pareto_frontier)

        # Rationale and explainable metrics
        assert report.recommendation_rationale != ""
        assert "RO-104" in report.recommendation_rationale

        # Verify dual certification flag on alternatives
        for alt in report.alternatives:
            assert isinstance(alt.is_verified, bool)
            assert isinstance(alt.is_fully_certified, bool)
            assert alt.gross_contribution_usd > Decimal("0.00")

    def test_full_shop_rescheduling_preserves_other_ros(
        self,
        validated_snapshot: DealershipSnapshotSchema,
        disruption_event_104: DisruptionEvent,
    ):
        """Verifies all shop ROs are evaluated and scheduled in the recovery plan."""
        pipeline = RecoveryReplanningPipeline()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        report = pipeline.execute_recovery(
            snapshot=validated_snapshot,
            disruption_event=disruption_event_104,
            evidence=ev,
        )

        assert report.recommended_option_id is not None
        recommended = next(a for a in report.alternatives if a.option_id == report.recommended_option_id)
        assigned_ro_ids = {a.ro_id for a in recommended.schedule_result.plan.assignments}

        # RO-101, RO-102, RO-103, RO-104 should all be scheduled (RO-105 is blocked by unfulfillable parts)
        for ro_id in ["RO-101", "RO-102", "RO-103", "RO-104"]:
            assert ro_id in assigned_ro_ids, f"{ro_id} was omitted from the rescheduled plan"

    def test_pareto_frontier_filtering_strictly_dominates(self):
        """Verifies mathematical correctness of 4D Pareto dominance filtering."""
        pipeline = RecoveryReplanningPipeline()

        # Candidate A: low lateness, low cost, high delta (Dominant)
        alt_a = RecoveryAlternative(
            option_id="OPT-A",
            plan_id="PLAN-A",
            sourcing_candidate=SourcingCandidate(
                option_id="OPT-A",
                offer_id="OFF-A",
                part_req_id="P1",
                supplier_id="SUP-A",
                supplier_name="Fast Supplier",
                unit_cost_usd=Decimal("100.00"),
                freight_surcharge_usd=Decimal("20.00"),
                total_sourcing_cost_usd=Decimal("120.00"),
                quoted_eta_tick=160,
                receiving_inspection_minutes=10,
                usable_ready_tick=162,
            ),
            schedule_result=None,
            gross_contribution_usd=Decimal("1000.00"),
            sourcing_cost_usd=Decimal("20.00"),
            lateness_penalty_usd=Decimal("0.00"),
            net_objective_usd=Decimal("980.00"),
            net_recovery_delta_usd=Decimal("200.00"),
            weighted_lateness_ticks=0,
            bay_blocked_hours=Decimal("1.0"),
            is_verified=True,
            is_fully_certified=True,
            certification_status="FULLY_CERTIFIED",
        )

        # Candidate B: strictly worse than A in every dimension (Dominated)
        alt_b = RecoveryAlternative(
            option_id="OPT-B",
            plan_id="PLAN-B",
            sourcing_candidate=SourcingCandidate(
                option_id="OPT-B",
                offer_id="OFF-B",
                part_req_id="P1",
                supplier_id="SUP-B",
                supplier_name="Slow Expensive Supplier",
                unit_cost_usd=Decimal("100.00"),
                freight_surcharge_usd=Decimal("50.00"),
                total_sourcing_cost_usd=Decimal("150.00"),
                quoted_eta_tick=190,
                receiving_inspection_minutes=10,
                usable_ready_tick=192,
            ),
            schedule_result=None,
            gross_contribution_usd=Decimal("1000.00"),
            sourcing_cost_usd=Decimal("50.00"),
            lateness_penalty_usd=Decimal("100.00"),
            net_objective_usd=Decimal("850.00"),
            net_recovery_delta_usd=Decimal("70.00"),
            weighted_lateness_ticks=40,
            bay_blocked_hours=Decimal("3.5"),
            is_verified=True,
            is_fully_certified=True,
            certification_status="FULLY_CERTIFIED",
        )

        # Candidate C: higher cost but zero lateness (Trade-off, Non-dominated)
        alt_c = RecoveryAlternative(
            option_id="OPT-C",
            plan_id="PLAN-C",
            sourcing_candidate=SourcingCandidate(
                option_id="OPT-C",
                offer_id="OFF-C",
                part_req_id="P1",
                supplier_id="SUP-C",
                supplier_name="Premium Hotshot",
                unit_cost_usd=Decimal("100.00"),
                freight_surcharge_usd=Decimal("80.00"),
                total_sourcing_cost_usd=Decimal("180.00"),
                quoted_eta_tick=155,
                receiving_inspection_minutes=5,
                usable_ready_tick=156,
            ),
            schedule_result=None,
            gross_contribution_usd=Decimal("1000.00"),
            sourcing_cost_usd=Decimal("80.00"),
            lateness_penalty_usd=Decimal("0.00"),
            net_objective_usd=Decimal("920.00"),
            net_recovery_delta_usd=Decimal("140.00"),
            weighted_lateness_ticks=0,
            bay_blocked_hours=Decimal("0.5"),  # Freed bay even earlier!
            is_verified=True,
            is_fully_certified=True,
            certification_status="FULLY_CERTIFIED",
        )

        pareto = pipeline._filter_pareto_frontier([alt_a, alt_b, alt_c])
        pareto_ids = {p.option_id for p in pareto}

        assert "OPT-A" in pareto_ids
        assert "OPT-C" in pareto_ids
        assert "OPT-B" not in pareto_ids, "Strictly dominated Candidate B must be excluded from Pareto frontier"

    def test_failure_safety_when_no_feasible_sourcing(
        self,
        validated_snapshot: DealershipSnapshotSchema,
    ):
        """Verifies graceful handling when all supplier offers are expired/inactive."""
        snap_copy = validated_snapshot.model_copy(deep=True)
        # Invalidate all offers
        for o in snap_copy.supplier_offers:
            o.quote_status = QuoteStatus.REJECTED

        disruption = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            trigger_tick=159,
        )

        pipeline = RecoveryReplanningPipeline()
        ev = make_synthetic_evidence(snap_copy, authorize_all=True)

        report = pipeline.execute_recovery(
            snapshot=snap_copy,
            disruption_event=disruption,
            evidence=ev,
        )

        assert report.recommended_option_id is None
        assert report.recommended_plan_id is None
        assert len(report.alternatives) == 0
        assert len(report.pareto_frontier) == 0
        assert "No feasible" in report.recommendation_rationale
        assert len(report.unresolved_risks) > 0
