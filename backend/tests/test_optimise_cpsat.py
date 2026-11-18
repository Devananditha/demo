"""Tests for T2 OR-Tools CP-SAT Discrete Scheduling Optimizer (Task 1.4 Corrected).

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md
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
from app.optimise.evidence import WorkshopEvidenceBundle
from app.optimise.heuristics import T1BitsetScheduler
from app.optimise.models import SchedulerTier, SolverStatus
from app.schemas.domain import DealershipSnapshotSchema, TaskStatus
from app.verifier.models import VerificationResult
from tests.optimise_test_utils import make_synthetic_evidence


class TestCPSATSchedulerCore:
    """Rigorous unit and property tests for the CP-SAT discrete scheduler."""

    def test_s_math_01_solve_and_dual_verification(self, validated_snapshot: DealershipSnapshotSchema):
        """Solves baseline S-MATH-01, verifying solver status, objective, and dual certification."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        scheduler = CPSATScheduler(config)
        result = scheduler.schedule(validated_snapshot, plan_id="PLAN-T2-TEST", evidence=evidence)

        assert result.plan_id == "PLAN-T2-TEST"
        assert result.solver_tier == SchedulerTier.T2_CPSAT
        assert result.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert result.objective_value_usd is not None

        # Dual Certification: L4 Sweep-Line Oracle AND Supplemental Audit
        assert result.is_verified is True
        assert result.verification_result is not None
        assert result.verification_result.is_valid is True
        assert result.is_fully_certified is True
        assert result.supplemental_audit_result is not None
        assert result.supplemental_audit_result["is_valid"] is True

    def test_c7_customer_authorization_hard_gate_cpsat(self, validated_snapshot: DealershipSnapshotSchema):
        """CP-SAT must strictly refuse to schedule unauthorized ROs."""
        scheduler = CPSATScheduler()

        # Authorize only RO-101
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=False, authorized_ro_ids={"RO-101"})
        result = scheduler.schedule(validated_snapshot, evidence=ev)

        scheduled_ros = {a.ro_id for a in result.plan.assignments}
        assert scheduled_ros == {"RO-101"}
        assert "RO-102" not in scheduled_ros
        assert "RO-103" not in scheduled_ros

    def test_c3_transitive_precedence_closure_cpsat(self, validated_snapshot: DealershipSnapshotSchema):
        """In CP-SAT, a successor task CANNOT be scheduled if its predecessor was excluded."""
        snap = validated_snapshot.model_copy(deep=True)
        # Invalidate parts for TASK-101-01 (predecessor)
        target_pred_id = "TASK-101-01"
        for p in snap.part_requirements:
            if p.task_id == target_pred_id:
                p.usable_ready_tick = None

        scheduler = CPSATScheduler()
        ev = make_synthetic_evidence(snap, authorize_all=True)
        result = scheduler.schedule(snap, evidence=ev)

        assert target_pred_id in result.unscheduled_tasks
        # Any task depending on target_pred_id must also be unscheduled
        for t in snap.tasks:
            if target_pred_id in t.predecessor_task_ids:
                assert t.task_id in result.unscheduled_tasks
                assert "PREDECESSOR_UNSCHEDULED" in result.unscheduled_tasks[t.task_id]

    def test_cpsat_objective_higher_or_equal_to_t1(self, validated_snapshot: DealershipSnapshotSchema):
        """T2 global optimizer must match or improve upon T1 constructive dispatch."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        t1_scheduler = T1BitsetScheduler(config)
        t2_scheduler = CPSATScheduler(config)

        t1_res = t1_scheduler.schedule(validated_snapshot, evidence=evidence)
        t2_res = t2_scheduler.schedule(validated_snapshot, evidence=evidence)

        assert t1_res.objective_value_usd is not None
        assert t2_res.objective_value_usd is not None
        assert t2_res.objective_value_usd >= t1_res.objective_value_usd

    def test_deterministic_reproducibility(self, validated_snapshot: DealershipSnapshotSchema):
        """Fixed random seed must yield identical schedule and objective across runs."""
        config = OptimiseConfig(time_budget_seconds=2.5, deterministic_seed=42)
        evidence = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        scheduler1 = CPSATScheduler(config)
        scheduler2 = CPSATScheduler(config)

        res1 = scheduler1.schedule(validated_snapshot, plan_id="PLAN-DETERM-1", evidence=evidence)
        res2 = scheduler2.schedule(validated_snapshot, plan_id="PLAN-DETERM-2", evidence=evidence)

        assert res1.solver_status == res2.solver_status
        assert res1.objective_value_usd == res2.objective_value_usd
        assert len(res1.plan.assignments) == len(res2.plan.assignments)

    def test_fallback_to_t1_on_l4_verification_rejection(self, validated_snapshot: DealershipSnapshotSchema):
        """If T2 candidate fails L4 verification, scheduler must safely fall back to verified T1."""
        scheduler = CPSATScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        with patch("app.optimise.cpsat_solver.SweepLineOracle") as mock_oracle_cls:
            mock_oracle_instance = mock_oracle_cls.return_value
            mock_oracle_instance.verify_plan.return_value = VerificationResult(
                plan_id="MOCKED-FAIL",
                snapshot_hash="hash",
                is_valid=False,
                violations=[],
                execution_time_ms=1.0,
            )

            result = scheduler.schedule(validated_snapshot, plan_id="PLAN-T2-FAIL-L4", evidence=ev)

            assert result.solver_tier == SchedulerTier.T1_HEURISTIC
            assert result.degradation_reason is not None
            assert "reverted to T1" in result.degradation_reason

    def test_fallback_to_t1_on_infeasible_status(self, validated_snapshot: DealershipSnapshotSchema):
        """If CP-SAT solver returns INFEASIBLE, scheduler must safely fall back to verified T1."""
        scheduler = CPSATScheduler()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        with patch("ortools.sat.python.cp_model.CpSolver.Solve") as mock_solve:
            mock_solve.return_value = cp_model.INFEASIBLE

            result = scheduler.schedule(validated_snapshot, plan_id="PLAN-T2-INFEASIBLE", evidence=ev)

            assert result.solver_tier == SchedulerTier.T1_HEURISTIC
            assert result.degradation_reason is not None
            assert "automatically degraded to verified T1 schedule" in result.degradation_reason
