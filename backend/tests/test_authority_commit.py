"""Unit and integration tests for Authority & OCC Commit Gateway.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md (Section 2.4)
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4.4)
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.5)
- docs/12_VERIFICATION_AND_REVALIDATION.md
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from app.authority.commit import AuthorityCommitGateway
from app.authority.models import (
    CommitRequest,
    CommitResult,
    CommitStatus,
    ManagerRecoveryApproval,
    OutboxEventType,
)
from app.optimise import ObjectiveMetrics, OptimiseConfig, ScheduleResult, SchedulerTier, SolverStatus
from app.recover.models import (
    DisruptionEvent,
    RecoveryAlternative,
    SourcingCandidate,
)
from app.recover.replan import RecoveryReplanningPipeline
from app.schemas.domain import DealershipSnapshotSchema
from app.verifier.models import CandidateSchedulePlan


@pytest.fixture
def mock_candidate() -> RecoveryAlternative:
    return RecoveryAlternative(
        option_id="OFFER-104-S1",
        plan_id="PLAN-REC-OFFER-104-S1",
        sourcing_candidate=SourcingCandidate(
            option_id="OFFER-104-S1",
            offer_id="OFFER-104-S1",
            part_req_id="PART-REQ-104-SOLENOID",
            supplier_id="S1_HOTSHOT",
            supplier_name="Regional Courier",
            unit_cost_usd=Decimal("120.00"),
            freight_surcharge_usd=Decimal("37.00"),
            total_sourcing_cost_usd=Decimal("157.00"),
            quoted_eta_tick=163,
            receiving_inspection_minutes=10,
            usable_ready_tick=165,
        ),
        schedule_result=ScheduleResult(
            plan_id="PLAN-REC-OFFER-104-S1",
            rooftop_id="ROOF-01",
            snapshot_hash="hash-abc-123",
            solver_tier=SchedulerTier.T2_CPSAT,
            solver_status=SolverStatus.FEASIBLE,
            runtime_ms=12.5,
            plan=CandidateSchedulePlan(
                plan_id="PLAN-REC-OFFER-104-S1",
                rooftop_id="ROOF-01",
                snapshot_hash="hash-abc-123",
                assignments=[],
            ),
            metrics=ObjectiveMetrics(
                gross_contribution_usd=Decimal("1000.00"),
                sourcing_cost_usd=Decimal("37.00"),
                weighted_lateness_ticks=51,
                lateness_penalty_usd=Decimal("127.50"),
                bay_blocked_ticks=0,
                bay_blocked_penalty_usd=Decimal("0.00"),
                net_objective_usd=Decimal("835.50"),
            ),
            is_verified=True,
            is_fully_certified=True,
            is_actionable=True,
        ),
        gross_contribution_usd=Decimal("1000.00"),
        sourcing_cost_usd=Decimal("37.00"),
        lateness_penalty_usd=Decimal("127.50"),
        net_objective_usd=Decimal("835.50"),
        net_recovery_delta_usd=Decimal("203.00"),
        weighted_lateness_ticks=51,
        bay_blocked_hours=Decimal("0.0"),
        is_verified=True,
        is_fully_certified=True,
        certification_status="FULLY_CERTIFIED",
    )


class TestAuthorityCommitGateway:
    """Test suite for atomic OCC commit gateway, manager bindings, and outbox event persistence."""

    def test_successful_authority_commit(
        self,
        validated_snapshot: DealershipSnapshotSchema,
        mock_candidate: RecoveryAlternative,
    ):
        """Verifies successful commit creates transactional outbox events and records in ledger."""
        gateway = AuthorityCommitGateway()
        snap_hash = validated_snapshot.snapshot_hash or "snap-valid-hash"

        approval = ManagerRecoveryApproval(
            plan_id=mock_candidate.plan_id,
            snapshot_hash=snap_hash,
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=2),
        )

        req = CommitRequest(
            plan_id=mock_candidate.plan_id,
            expected_snapshot_hash=snap_hash,
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
        )

        res = gateway.commit_recovery_plan(
            request=req,
            current_snapshot=validated_snapshot,
            candidate_alternative=mock_candidate,
            approval=approval,
        )

        assert res.status == CommitStatus.COMMITTED
        assert res.plan_id == mock_candidate.plan_id
        assert len(res.outbox_events) >= 2
        assert any(e.event_type == OutboxEventType.DISPATCH_PLAN_COMMITTED for e in res.outbox_events)
        assert any(e.event_type == OutboxEventType.SUPPLIER_ORDER_EXPEDITED for e in res.outbox_events)

        # Gateway ledger must record this commit
        assert gateway.get_ledger_entry(req.plan_id, snap_hash) is not None

    def test_idempotent_replay(
        self,
        validated_snapshot: DealershipSnapshotSchema,
        mock_candidate: RecoveryAlternative,
    ):
        """Verifies submitting the exact same commit request replays original result without re-executing."""
        gateway = AuthorityCommitGateway()
        snap_hash = validated_snapshot.snapshot_hash or "snap-valid-hash"

        approval = ManagerRecoveryApproval(
            plan_id=mock_candidate.plan_id,
            snapshot_hash=snap_hash,
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=2),
        )

        req = CommitRequest(
            plan_id=mock_candidate.plan_id,
            expected_snapshot_hash=snap_hash,
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
        )

        first_res = gateway.commit_recovery_plan(
            request=req,
            current_snapshot=validated_snapshot,
            candidate_alternative=mock_candidate,
            approval=approval,
        )
        second_res = gateway.commit_recovery_plan(
            request=req,
            current_snapshot=validated_snapshot,
            candidate_alternative=mock_candidate,
            approval=approval,
        )

        assert first_res.status == CommitStatus.COMMITTED
        assert second_res.status == CommitStatus.COMMITTED
        assert first_res.committed_at == second_res.committed_at
        assert len(gateway.get_outbox_events()) == len(first_res.outbox_events)

    def test_occ_stale_snapshot_abort(
        self,
        validated_snapshot: DealershipSnapshotSchema,
        mock_candidate: RecoveryAlternative,
    ):
        """Verifies OCC abort when state snapshot has mutated since calculation."""
        gateway = AuthorityCommitGateway()

        approval = ManagerRecoveryApproval(
            plan_id=mock_candidate.plan_id,
            snapshot_hash="STALE_OLD_HASH_123",
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=2),
        )

        # Mutate the expected snapshot hash to simulate stale state
        req = CommitRequest(
            plan_id=mock_candidate.plan_id,
            expected_snapshot_hash="STALE_OLD_HASH_123",
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
        )

        res = gateway.commit_recovery_plan(
            request=req,
            current_snapshot=validated_snapshot,
            candidate_alternative=mock_candidate,
            approval=approval,
        )

        assert res.status == CommitStatus.ABORTED_STALE_STATE
        assert res.error_code == "OCC_VERSION_MISMATCH"
        assert len(res.outbox_events) == 0
        assert "state changed while reviewing proposal" in res.error_message

    def test_uncertified_candidate_rejection(
        self,
        validated_snapshot: DealershipSnapshotSchema,
        mock_candidate: RecoveryAlternative,
    ):
        """Verifies uncertified or failing candidate is immediately rejected."""
        gateway = AuthorityCommitGateway()
        snap_hash = validated_snapshot.snapshot_hash or "snap-valid-hash"

        uncertified_cand = mock_candidate.model_copy(deep=True)
        uncertified_cand.is_fully_certified = False

        approval = ManagerRecoveryApproval(
            plan_id=uncertified_cand.plan_id,
            snapshot_hash=snap_hash,
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=2),
        )

        req = CommitRequest(
            plan_id=uncertified_cand.plan_id,
            expected_snapshot_hash=snap_hash,
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
        )

        res = gateway.commit_recovery_plan(
            request=req,
            current_snapshot=validated_snapshot,
            candidate_alternative=uncertified_cand,
            approval=approval,
        )

        assert res.status == CommitStatus.REJECTED_UNCERTIFIED
        assert "not certified" in res.error_code or "failed independent" in res.error_message

    def test_missing_or_expired_manager_approval(
        self,
        validated_snapshot: DealershipSnapshotSchema,
        mock_candidate: RecoveryAlternative,
    ):
        """Verifies rejection when required manager approval is missing or expired."""
        gateway = AuthorityCommitGateway()
        snap_hash = validated_snapshot.snapshot_hash or "snap-valid-hash"

        # 1. Missing approver_id
        req_missing = CommitRequest(
            plan_id=mock_candidate.plan_id,
            expected_snapshot_hash=snap_hash,
            approver_id="   ",
        )
        res_missing = gateway.commit_recovery_plan(
            request=req_missing,
            current_snapshot=validated_snapshot,
            candidate_alternative=mock_candidate,
            approval=None,
        )
        assert res_missing.status == CommitStatus.REJECTED_UNAUTHORIZED

        # 2. Expired approval
        approval_expired = ManagerRecoveryApproval(
            plan_id=mock_candidate.plan_id,
            snapshot_hash=snap_hash,
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
            valid_until=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        req_expired = CommitRequest(
            plan_id=mock_candidate.plan_id,
            expected_snapshot_hash=snap_hash,
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
        )
        res_expired = gateway.commit_recovery_plan(
            request=req_expired,
            current_snapshot=validated_snapshot,
            candidate_alternative=mock_candidate,
            approval=approval_expired,
        )
        assert res_expired.status == CommitStatus.REJECTED_EXPIRED
