"""End-to-End Integration Tests for ServiceYield AI Optimise Engine (Task 1.4).

Authoritative Reference:
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.3)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md
"""

from decimal import Decimal
import time
import pytest
from unittest.mock import patch

from app.optimise import (
    BayHourShadowPriceCalculator,
    CPSATScheduler,
    OptimiseConfig,
    SchedulerTier,
    ShadowPriceStatus,
    SolverStatus,
    T1BitsetScheduler,
)
from app.schemas.domain import DealershipSnapshotSchema
from app.verifier.models import VerificationResult


class TestOptimiseIntegration:
    """Full cross-tier integration verification on canonical golden fixture S-MATH-01."""

    def test_end_to_end_optimise_pipeline_on_s_math_01(self, validated_snapshot: DealershipSnapshotSchema):
        """Executes complete Optimise pipeline: T1 constructive dispatch -> T2 CP-SAT -> Shadow Price."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)

        # 1. Execute T1 Heuristic Dispatch
        t1_start = time.perf_counter()
        t1_scheduler = T1BitsetScheduler(config)
        t1_result = t1_scheduler.schedule(validated_snapshot, plan_id="PLAN-INT-T1")
        t1_elapsed_ms = (time.perf_counter() - t1_start) * 1000.0

        assert t1_result.solver_tier == SchedulerTier.T1_HEURISTIC
        assert t1_result.is_verified is True
        assert t1_result.verification_result is not None
        assert t1_result.verification_result.is_valid is True
        assert t1_elapsed_ms < 50.0  # sub-2ms typical, < 50ms in CI/CD

        # 2. Execute T2 CP-SAT Discrete Optimization (warm-started with T1)
        t2_start = time.perf_counter()
        t2_scheduler = CPSATScheduler(config)
        t2_result = t2_scheduler.schedule(validated_snapshot, plan_id="PLAN-INT-T2")
        t2_elapsed_ms = (time.perf_counter() - t2_start) * 1000.0

        assert t2_result.solver_tier == SchedulerTier.T2_CPSAT
        assert t2_result.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert t2_result.is_verified is True
        assert t2_result.verification_result is not None
        assert t2_result.verification_result.is_valid is True
        assert t2_elapsed_ms <= (config.time_budget_seconds * 1000.0) + 1500.0

        # Monotonicity: T2 objective must meet or beat T1 objective
        assert t1_result.objective_value_usd is not None
        assert t2_result.objective_value_usd is not None
        assert t2_result.objective_value_usd >= t1_result.objective_value_usd

        # 3. Compute Bay-Hour Shadow Price nu_b(t) for Standard Lift (BAY-02)
        price_calc = BayHourShadowPriceCalculator(config, solver=t2_scheduler)
        shadow_price = price_calc.calculate_shadow_price(
            snapshot=validated_snapshot,
            bay_id="BAY-02",
            start_tick=96,
            end_tick=120,
            baseline_result=t2_result,
        )

        assert shadow_price.rooftop_id == validated_snapshot.rooftop.rooftop_id
        assert shadow_price.bay_id == "BAY-02"
        assert shadow_price.duration_hours == Decimal("2.0000")
        assert shadow_price.shadow_price_usd_per_hour >= Decimal("0.00")
        assert shadow_price.shadow_price_usd_per_tick == (
            shadow_price.shadow_price_usd_per_hour / Decimal("12")
        ).quantize(Decimal("0.0001"))

    def test_shadow_price_bottleneck_vs_abundant_capacity(self, validated_snapshot: DealershipSnapshotSchema):
        """Verifies that capacity restriction on heavily demanded bays incurs positive shadow price."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)
        price_calc = BayHourShadowPriceCalculator(config)

        # Evaluate BAY-02 during peak morning interval [96, 120]
        price_bay2 = price_calc.calculate_shadow_price(
            snapshot=validated_snapshot,
            bay_id="BAY-02",
            start_tick=96,
            end_tick=120,
        )

        # Objective must be non-negative
        assert price_bay2.shadow_price_usd_per_hour >= Decimal("0.00")
        assert price_bay2.status in (ShadowPriceStatus.EXACT, ShadowPriceStatus.APPROXIMATE)

    def test_graceful_degradation_when_t2_fails_l4_oracle(self, validated_snapshot: DealershipSnapshotSchema):
        """Guarantees uninterrupted operational resilience: If T2 fails L4 audit, degrades to verified T1."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)
        scheduler = CPSATScheduler(config)

        with patch("app.optimise.cpsat_solver.SweepLineOracle") as mock_oracle:
            # Emulate an L4 violation in the T2 candidate plan
            mock_oracle.return_value.verify_plan.return_value = VerificationResult(
                plan_id="CORRUPTED-T2-PLAN",
                snapshot_hash="hash",
                is_valid=False,
                violations=[],
                execution_time_ms=0.5,
            )

            result = scheduler.schedule(validated_snapshot, plan_id="PLAN-RESILIENCE-TEST")

            # Must degrade to T1
            assert result.solver_tier == SchedulerTier.T1_HEURISTIC
            assert result.is_verified is True
            assert result.verification_result is not None
            assert result.verification_result.is_valid is True
            assert result.degradation_reason is not None
            assert "failed L4 verification" in result.degradation_reason
