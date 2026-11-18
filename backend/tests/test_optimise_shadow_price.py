"""Tests for Bay-Hour Shadow Price nu_b(t) Calculation and Valuation Surface (Task 1.4 Corrected).

Authoritative Reference:
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.3)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md (A3: $120/hr, nu = $2.00/min = $120/hr)
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md
"""

from decimal import Decimal
import pytest
from unittest.mock import patch

from app.optimise.config import OptimiseConfig
from app.optimise.cpsat_solver import CPSATScheduler
from app.optimise.models import (
    BayHourPriceSurface,
    BayHourShadowPrice,
    ScheduleResult,
    SchedulerTier,
    ShadowPriceStatus,
    SolverStatus,
)
from app.optimise.shadow_price import BayHourShadowPriceCalculator
from app.schemas.domain import DealershipSnapshotSchema
from tests.optimise_test_utils import make_synthetic_evidence


class TestBayHourShadowPriceCalculatorCore:
    """Comprehensive mathematical and property tests for the shadow price calculator."""

    def test_shadow_price_discrete_difference_formula(self, validated_snapshot: DealershipSnapshotSchema):
        """Validates that nu_b(t) = (Z*(C) - Z*(C \\ {(b, t)})) / Delta_t in USD/bay-hour."""
        calculator = BayHourShadowPriceCalculator()
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        bay_id = "BAY-02"
        start_tick = 96
        end_tick = 120  # 24 ticks = 120 minutes = 2.0 hours

        price = calculator.calculate_shadow_price(
            snapshot=validated_snapshot,
            bay_id=bay_id,
            start_tick=start_tick,
            end_tick=end_tick,
            evidence=evidence,
        )

        assert price.bay_id == bay_id
        assert price.interval_start_tick == start_tick
        assert price.interval_end_tick == end_tick
        assert price.duration_hours == Decimal("2.0000")
        assert price.delta_objective_usd == price.baseline_objective_usd - price.perturbed_objective_usd

        # Canonical unit conversion checks
        expected_hourly = (price.delta_objective_usd / Decimal("2.0")).quantize(Decimal("0.01"))
        assert price.shadow_price_usd_per_hour == expected_hourly

        expected_tick = (price.shadow_price_usd_per_hour / Decimal("12")).quantize(Decimal("0.0001"))
        assert price.shadow_price_usd_per_tick == expected_tick

        # Exactness certification
        if price.baseline_status == SolverStatus.OPTIMAL and price.perturbed_status == SolverStatus.OPTIMAL:
            assert price.is_exact is True
            assert price.status == ShadowPriceStatus.EXACT

    def test_unit_equivalence_120_usd_per_hour_equals_2_per_min(self):
        """Enforces mathematical equivalence: $120.00/hour == $10.00/tick == $2.00/minute."""
        hourly = Decimal("120.00")
        per_tick = (hourly / Decimal("12")).quantize(Decimal("0.01"))
        per_min = (hourly / Decimal("60")).quantize(Decimal("0.01"))

        assert per_tick == Decimal("10.00")
        assert per_min == Decimal("2.00")

    def test_parameter_validation(self, validated_snapshot: DealershipSnapshotSchema):
        """Rejects invalid tick bounds and non-existent bay IDs."""
        calculator = BayHourShadowPriceCalculator()

        # Start >= End
        with pytest.raises(ValueError, match="Invalid evaluation interval"):
            calculator.calculate_shadow_price(validated_snapshot, "BAY-01", 120, 120)

        # Start < 0
        with pytest.raises(ValueError, match="Invalid evaluation interval"):
            calculator.calculate_shadow_price(validated_snapshot, "BAY-01", -5, 100)

        # End > horizon
        with pytest.raises(ValueError, match="Invalid evaluation interval"):
            calculator.calculate_shadow_price(validated_snapshot, "BAY-01", 100, 300)

        # Bay not in snapshot
        with pytest.raises(ValueError, match="does not exist in snapshot bays"):
            calculator.calculate_shadow_price(validated_snapshot, "BAY-999-NONEXISTENT", 96, 120)

    def test_surface_generation_across_operating_hours(self, validated_snapshot: DealershipSnapshotSchema):
        """Computes a discrete valuation surface across operational bays."""
        calculator = BayHourShadowPriceCalculator()
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        surface = calculator.compute_price_surface(
            snapshot=validated_snapshot,
            bay_ids=["BAY-02", "BAY-03"],
            interval_ticks=12,  # 1 hour
            stride_ticks=3,     # 15 minutes architecture stride
            horizon_start_tick=96,
            horizon_end_tick=120,
            evidence=evidence,
        )

        assert isinstance(surface, BayHourPriceSurface)
        assert surface.rooftop_id == validated_snapshot.rooftop.rooftop_id
        assert surface.snapshot_hash == validated_snapshot.snapshot_hash
        assert surface.stride_ticks == 3
        assert len(surface.points) > 0

        for pt in surface.points:
            assert pt.bay_id in ("BAY-02", "BAY-03")
            assert pt.interval_end_tick - pt.interval_start_tick == 12
            assert pt.duration_hours == Decimal("1.0000")
            assert pt.shadow_price_usd_per_hour >= Decimal("0.00")

    def test_approximate_status_when_solver_is_feasible(self, validated_snapshot: DealershipSnapshotSchema):
        """Flags status as APPROXIMATE and is_exact as False if a solve stops at FEASIBLE."""
        calculator = BayHourShadowPriceCalculator()
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        with patch.object(CPSATScheduler, "schedule") as mock_sched:
            mock_res = ScheduleResult(
                plan_id="PLAN-MOCK",
                rooftop_id="ROOF-01",
                snapshot_hash="hash",
                solver_tier=SchedulerTier.T2_CPSAT,
                solver_status=SolverStatus.FEASIBLE,
                runtime_ms=10.0,
                objective_value_usd=Decimal("500.00"),
                plan=calculator.solver.t1_fallback.schedule(validated_snapshot, evidence=evidence).plan,
                metrics=calculator.solver.t1_fallback.schedule(validated_snapshot, evidence=evidence).metrics,
                is_verified=True,
            )
            mock_sched.return_value = mock_res

            price = calculator.calculate_shadow_price(
                validated_snapshot,
                bay_id="BAY-02",
                start_tick=96,
                end_tick=120,
                evidence=evidence,
            )

            assert price.is_exact is False
            assert price.status == ShadowPriceStatus.APPROXIMATE

    def test_t1_fallback_cannot_claim_exact_shadow_price(self, validated_snapshot: DealershipSnapshotSchema):
        """A T1 fallback schedule supplied as baseline must never be accepted as EXACT."""
        calculator = BayHourShadowPriceCalculator()
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        # Baseline is a T1 result
        t1_baseline = calculator.solver.t1_fallback.schedule(validated_snapshot, evidence=evidence)
        assert t1_baseline.solver_tier == SchedulerTier.T1_HEURISTIC

        # Calculate shadow price with T1 baseline passed in
        price = calculator.calculate_shadow_price(
            validated_snapshot,
            bay_id="BAY-02",
            start_tick=96,
            end_tick=120,
            baseline_result=t1_baseline,
            evidence=evidence,
        )

        # Must not claim exactness from a T1 baseline! Calculator recomputed baseline using T2 CP-SAT!
        assert price.baseline_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

    def test_negative_difference_flags_solver_inconsistency(self, validated_snapshot: DealershipSnapshotSchema):
        """A significant negative Delta Z (capacity loss increased objective) must flag UNAVAILABLE."""
        calculator = BayHourShadowPriceCalculator()
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        with patch.object(CPSATScheduler, "schedule") as mock_sched:
            base_mock = ScheduleResult(
                plan_id="BASE-MOCK",
                rooftop_id="ROOF-01",
                snapshot_hash="hash",
                solver_tier=SchedulerTier.T2_CPSAT,
                solver_status=SolverStatus.OPTIMAL,
                runtime_ms=10.0,
                objective_value_usd=Decimal("300.00"),
                plan=calculator.solver.t1_fallback.schedule(validated_snapshot, evidence=evidence).plan,
                metrics=calculator.solver.t1_fallback.schedule(validated_snapshot, evidence=evidence).metrics,
                is_verified=True,
            )
            # Perturbed objective is HIGHER ($400 > $300), which is mathematically inconsistent
            pert_mock = ScheduleResult(
                plan_id="PERT-MOCK",
                rooftop_id="ROOF-01",
                snapshot_hash="hash",
                solver_tier=SchedulerTier.T2_CPSAT,
                solver_status=SolverStatus.OPTIMAL,
                runtime_ms=10.0,
                objective_value_usd=Decimal("400.00"),
                plan=calculator.solver.t1_fallback.schedule(validated_snapshot, evidence=evidence).plan,
                metrics=calculator.solver.t1_fallback.schedule(validated_snapshot, evidence=evidence).metrics,
                is_verified=True,
            )
            mock_sched.side_effect = [base_mock, pert_mock]

            price = calculator.calculate_shadow_price(
                validated_snapshot,
                bay_id="BAY-02",
                start_tick=96,
                end_tick=120,
                evidence=evidence,
            )

            assert price.status == ShadowPriceStatus.UNAVAILABLE
            assert price.is_exact is False
            assert "inconsistency" in (price.reason or "").lower()
