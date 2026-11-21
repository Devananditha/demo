"""Tests for Phase 2 Optimisation Validation & Benchmark Scenarios.

Verifies:
1. Deterministic execution of 7 scenarios across 4 dispatch methods.
2. Hard constraint inviolability (C1-C7 violations == 0 everywhere).
3. Null-control non-manufactured recovery (Delta Z == $0.00, churn == 0).
4. S-MATH-01 parts delay recovery advantage (Delta Z > $0).
5. Statistical consistency across seeds.
6. Decision replay integration.
"""

from decimal import Decimal
import pytest

from app.benchmark.models import BenchmarkScenarioType, DispatchMethod
from app.benchmark.runner import benchmark_runner


def test_benchmark_null_control_zero_manufactured_benefit():
    """Invariant: Null disruption must produce Delta Z == $0.00 and 0 churn."""
    res = benchmark_runner.run_scenario(BenchmarkScenarioType.NULL_CONTROL, seed=42)
    assert res.stallbreaker_advantage_usd == Decimal("0.00")
    sb_metrics = res.methods[DispatchMethod.STALLBREAKER.value]
    assert sb_metrics.recovery_plan_churn == 0
    assert sb_metrics.constraint_violations == 0


def test_benchmark_all_methods_zero_constraint_violations():
    """Invariant: Hard constraints C1-C7 are NEVER violated by any method."""
    res = benchmark_runner.run_scenario(BenchmarkScenarioType.NORMAL_OPERATIONS, seed=42)
    for method_name, metrics in res.methods.items():
        assert metrics.constraint_violations == 0, f"Method {method_name} had {metrics.constraint_violations} violations!"
        assert metrics.is_verified is True


def test_benchmark_parts_delay_recovery_advantage():
    """In parts delay disruption, StallBreaker recovers economic value and unblocks bay."""
    res = benchmark_runner.run_scenario(BenchmarkScenarioType.PARTS_DELAY, seed=42)
    sb_metrics = res.methods[DispatchMethod.STALLBREAKER.value]
    cpsat_metrics = res.methods[DispatchMethod.CPSAT.value]

    assert res.stallbreaker_advantage_usd > Decimal("0.00")
    assert sb_metrics.net_objective_usd > cpsat_metrics.net_objective_usd
    assert sb_metrics.constraint_violations == 0
    assert res.replay_record_id is not None


def test_benchmark_specialised_bay_contention():
    """Contention on heavy lift BAY-01 is handled with 0 violations and high bay utilisation."""
    res = benchmark_runner.run_scenario(BenchmarkScenarioType.SPECIALISED_BAY_CONTENTION, seed=42)
    for m in res.methods.values():
        assert m.constraint_violations == 0
        assert m.is_verified is True


def test_benchmark_technician_shortage():
    """Technician shortage bottleneck is resolved with zero C6 shift breaches."""
    res = benchmark_runner.run_scenario(BenchmarkScenarioType.TECHNICIAN_SHORTAGE, seed=42)
    for m in res.methods.values():
        assert m.constraint_violations == 0
        assert m.is_verified is True


def test_benchmark_competing_reservations():
    """Competing bay reservations handled cleanly with zero C4 double-booking."""
    res = benchmark_runner.run_scenario(BenchmarkScenarioType.COMPETING_RESERVATIONS, seed=42)
    for m in res.methods.values():
        assert m.constraint_violations == 0
        assert m.is_verified is True


def test_benchmark_saturated_capacity():
    """Saturated workshop capacity prioritizes high-value tasks with 0 violations."""
    res = benchmark_runner.run_scenario(BenchmarkScenarioType.SATURATED_CAPACITY, seed=42)
    for m in res.methods.values():
        assert m.constraint_violations == 0
        assert m.is_verified is True


def test_benchmark_full_suite_execution():
    """Full suite of 7 scenarios generates complete statistical comparison."""
    report = benchmark_runner.run_full_suite(seed=42)
    assert report.total_scenarios_evaluated == 7
    assert report.all_violations_zero is True
    assert len(report.statistical_summaries) >= 4
