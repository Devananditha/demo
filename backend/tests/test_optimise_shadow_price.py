"""Tests for Bay-Hour Shadow Price nu_b(t) Calculation and Valuation Surface (Task 1.4).

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


class TestBayHourShadowPriceCalculator:
    """Comprehensive mathematical and property tests for the shadow price calculator."""

    def test_shadow_price_discrete_difference_formula(self, validated_snapshot: DealershipSnapshotSchema):
        """Validates that nu_b(t) = (Z*(C) - Z*(C \\ {(b, t)})) / Delta_t in USD/bay-hour."""
        calculator = BayHourShadowPriceCalculator()
        bay_id = "BAY-02"
        start_tick = 96
        end_tick = 120  # 24 ticks = 120 minutes = 2.0 hours

        price = calculator.calculate_shadow_price(
            snapshot=validated_snapshot,
            bay_id=bay_id,
            start_tick=start_tick,
            end_tick=end_tick,
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
        """Computes a discrete 1-hour valuation surface across operational bays."""
        calculator = BayHourShadowPriceCalculator()
        surface = calculator.compute_price_surface(
            snapshot=validated_snapshot,
            bay_ids=["BAY-02", "BAY-03"],
            interval_ticks=12,  # 1 hour
            stride_ticks=24,    # 2 hours
            horizon_start_tick=96,
            horizon_end_tick=144,
        )

        assert isinstance(surface, BayHourPriceSurface)
        assert surface.rooftop_id == validated_snapshot.rooftop.rooftop_id
        assert surface.snapshot_hash == validated_snapshot.snapshot_hash
        assert len(surface.points) > 0

        for pt in surface.points:
            assert pt.bay_id in ("BAY-02", "BAY-03")
            assert pt.interval_end_tick - pt.interval_start_tick == 12
            assert pt.duration_hours == Decimal("1.0000")
            assert pt.shadow_price_usd_per_hour >= Decimal("0.00")

    def test_approximate_status_when_solver_is_feasible(self, validated_snapshot: DealershipSnapshotSchema):
        """Flags status as APPROXIMATE and is_exact as False if a solve stops at FEASIBLE."""
        calculator = BayHourShadowPriceCalculator()

        # Mock solver to return FEASIBLE instead of OPTIMAL
        with patch.object(CPSATScheduler, "schedule") as mock_sched:
            mock_res = ScheduleResult(
                plan_id="PLAN-MOCK",
                rooftop_id="ROOF-01",
                snapshot_hash="hash",
                solver_tier=SchedulerTier.T2_CPSAT,
                solver_status=SolverStatus.FEASIBLE,
                runtime_ms=10.0,
                objective_value_usd=Decimal("500.00"),
                plan=calculator.solver.t1_fallback.schedule(validated_snapshot).plan,
                metrics=calculator.solver.t1_fallback.schedule(validated_snapshot).metrics,
                is_verified=True,
            )
            mock_sched.return_value = mock_res

            price = calculator.calculate_shadow_price(
                validated_snapshot,
                bay_id="BAY-02",
                start_tick=96,
                end_tick=120,
            )

            assert price.is_exact is False
            assert price.status == ShadowPriceStatus.APPROXIMATE

    def test_unavailable_status_when_solver_is_unknown(self, validated_snapshot: DealershipSnapshotSchema):
        """Flags status as UNAVAILABLE and is_exact as False if a solve returns UNKNOWN/INFEASIBLE."""
        calculator = BayHourShadowPriceCalculator()

        with patch.object(CPSATScheduler, "schedule") as mock_sched:
            mock_res = ScheduleResult(
                plan_id="PLAN-MOCK",
                rooftop_id="ROOF-01",
                snapshot_hash="hash",
                solver_tier=SchedulerTier.T1_HEURISTIC,
                solver_status=SolverStatus.UNKNOWN,
                runtime_ms=10.0,
                objective_value_usd=Decimal("0.00"),
                plan=calculator.solver.t1_fallback.schedule(validated_snapshot).plan,
                metrics=calculator.solver.t1_fallback.schedule(validated_snapshot).metrics,
                is_verified=True,
            )
            mock_sched.return_value = mock_res

            price = calculator.calculate_shadow_price(
                validated_snapshot,
                bay_id="BAY-02",
                start_tick=96,
                end_tick=120,
            )

            assert price.is_exact is False
            assert price.status == ShadowPriceStatus.UNAVAILABLE
            assert price.shadow_price_usd_per_hour == Decimal("0.00")
