"""Tests for T2 OR-Tools CP-SAT Discrete Scheduling Optimizer (Task 1.4).

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 3: Optimise)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md
"""

from decimal import Decimal
import pytest
from unittest.mock import patch
from ortools.sat.python import cp_model

from app.optimise.config import OptimiseConfig
from app.optimise.cpsat_solver import CPSATScheduler
from app.optimise.heuristics import T1BitsetScheduler
from app.optimise.models import SchedulerTier, SolverStatus
from app.schemas.domain import DealershipSnapshotSchema
from app.verifier.models import VerificationResult


class TestCPSATScheduler:
    """Rigorous unit and property tests for the CP-SAT discrete scheduler."""

    def test_s_math_01_solve_and_verification(self, validated_snapshot: DealershipSnapshotSchema):
        """Solves baseline S-MATH-01, verifying solver status, objective, and L4 certification."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)
        scheduler = CPSATScheduler(config)
        result = scheduler.schedule(validated_snapshot, plan_id="PLAN-T2-TEST")

        assert result.plan_id == "PLAN-T2-TEST"
        assert result.solver_tier == SchedulerTier.T2_CPSAT
        assert result.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.runtime_ms <= (config.time_budget_seconds * 1000.0) + 1000.0
        assert result.objective_value_usd is not None

        # Economic Metrics Validation
        assert result.metrics.gross_contribution_usd >= Decimal("0.00")
        assert result.metrics.net_objective_usd == (
            result.metrics.gross_contribution_usd - result.metrics.lateness_penalty_usd
        )

        # L4 Independent Verification
        assert result.is_verified is True
        assert result.verification_result is not None
        assert result.verification_result.is_valid is True
        assert result.verification_result.total_violations == 0

    def test_cpsat_objective_higher_or_equal_to_t1(self, validated_snapshot: DealershipSnapshotSchema):
        """T2 global optimizer must match or improve upon T1 constructive dispatch."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)
        t1_scheduler = T1BitsetScheduler(config)
        t2_scheduler = CPSATScheduler(config)

        t1_res = t1_scheduler.schedule(validated_snapshot)
        t2_res = t2_scheduler.schedule(validated_snapshot)

        assert t1_res.objective_value_usd is not None
        assert t2_res.objective_value_usd is not None
        assert t2_res.objective_value_usd >= t1_res.objective_value_usd

    def test_deterministic_reproducibility(self, validated_snapshot: DealershipSnapshotSchema):
        """Fixed random seed must yield identical schedule and objective across runs."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)
        scheduler1 = CPSATScheduler(config)
        scheduler2 = CPSATScheduler(config)

        res1 = scheduler1.schedule(validated_snapshot, plan_id="PLAN-DETERM-1")
        res2 = scheduler2.schedule(validated_snapshot, plan_id="PLAN-DETERM-2")

        assert res1.solver_status == res2.solver_status
        assert res1.objective_value_usd == res2.objective_value_usd
        assert len(res1.plan.assignments) == len(res2.plan.assignments)

        for a1, a2 in zip(res1.plan.assignments, res2.plan.assignments):
            assert a1.task_id == a2.task_id
            assert a1.bay_id == a2.bay_id
            assert a1.tech_id == a2.tech_id
            assert a1.start_tick == a2.start_tick
            assert a1.end_tick == a2.end_tick

    def test_c1_c7_hard_constraints_honored(self, validated_snapshot: DealershipSnapshotSchema):
        """Inspects CP-SAT assignments to verify physical and operational constraints."""
        scheduler = CPSATScheduler()
        result = scheduler.schedule(validated_snapshot)

        bays_by_id = {b.bay_id: b for b in validated_snapshot.bays}
        techs_by_id = {t.tech_id: t for t in validated_snapshot.technicians}
        tasks_by_id = {t.task_id: t for t in validated_snapshot.tasks}

        for a in result.plan.assignments:
            task = tasks_by_id[a.task_id]
            tech = techs_by_id[a.tech_id]
            bay = bays_by_id[a.bay_id]

            # C1 Skills Match
            assert task.required_skill in tech.skill_certifications
            # C1 Bay Type Match
            assert bay.bay_type == task.required_bay_type
            # C6 Shift Match
            assert a.start_tick >= tech.shift_start_tick
            assert a.end_tick <= tech.shift_end_tick
            # C6 Lunch Break Non-overlap
            lunch_start = tech.lunch_start_tick
            lunch_end = tech.lunch_start_tick + tech.lunch_duration_ticks
            assert not (max(a.start_tick, lunch_start) < min(a.end_tick, lunch_end))

    def test_externally_blocked_bay_respected(self, validated_snapshot: DealershipSnapshotSchema):
        """Perturbed solves with externally blocked bays must never schedule tasks in the blocked window."""
        scheduler = CPSATScheduler()
        blocked_bay = "BAY-02"
        b_start = 96
        b_end = 120

        result = scheduler.schedule(
            validated_snapshot,
            plan_id="PLAN-PERTURBED",
            blocked_bay_intervals=[(blocked_bay, b_start, b_end)],
        )

        for a in result.plan.assignments:
            if a.bay_id == blocked_bay:
                assert not (max(a.start_tick, b_start) < min(a.end_tick, b_end))

    def test_fallback_to_t1_on_l4_verification_rejection(self, validated_snapshot: DealershipSnapshotSchema):
        """If T2 candidate fails L4 verification, scheduler must safely fall back to verified T1."""
        scheduler = CPSATScheduler()

        # Mock SweepLineOracle to fail on T2 candidate plan
        with patch("app.optimise.cpsat_solver.SweepLineOracle") as mock_oracle_cls:
            mock_oracle_instance = mock_oracle_cls.return_value
            # When verifying the T2 plan, report invalid
            mock_oracle_instance.verify_plan.return_value = VerificationResult(
                plan_id="MOCKED-FAIL",
                snapshot_hash="hash",
                is_valid=False,
                violations=[],
                execution_time_ms=1.0,
            )

            result = scheduler.schedule(validated_snapshot, plan_id="PLAN-T2-FAIL-L4")

            # Should degrade to T1 fallback
            assert result.solver_tier == SchedulerTier.T1_HEURISTIC
            assert result.degradation_reason is not None
            assert "reverted to T1" in result.degradation_reason

    def test_fallback_to_t1_on_infeasible_or_unknown_status(self, validated_snapshot: DealershipSnapshotSchema):
        """If CP-SAT solver returns INFEASIBLE or UNKNOWN, scheduler must safely fall back to verified T1."""
        scheduler = CPSATScheduler()

        with patch("ortools.sat.python.cp_model.CpSolver.Solve") as mock_solve:
            # Force solver to return INFEASIBLE
            mock_solve.return_value = cp_model.INFEASIBLE

            result = scheduler.schedule(validated_snapshot, plan_id="PLAN-T2-INFEASIBLE")

            assert result.solver_tier == SchedulerTier.T1_HEURISTIC
            assert result.degradation_reason is not None
            assert "automatically degraded to verified T1 schedule" in result.degradation_reason
