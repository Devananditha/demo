"""StallBreaker Approval Gateway with Version-Binding and Safety Guards.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4.2 & 6)
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.6)
- docs/12_VERIFICATION_AND_REVALIDATION.md

Guarantees:
1. Version Binding: Rejects approvals if dealership snapshot hash mutated (OCC mismatch).
2. Freight Authority: Enforces manager approval threshold ($50.00) under constraint C7.
3. Transactional Outbox: Dispatches typed events for inventory hold and dispatch update.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.authority.commit import AuthorityCommitGateway
from app.authority.models import CommitRequest, CommitResult, CommitStatus, ManagerRecoveryApproval
from app.recover.models import RecoveryAlternative
from app.schemas.domain import DealershipSnapshotSchema
from app.stallbreaker.models import StallBreakerApprovalRequest


class StallBreakerApprovalGateway:
    """Safely records manager authorizations and executes OCC-guarded plan commits."""

    def __init__(self, commit_gateway: Optional[AuthorityCommitGateway] = None):
        self.gateway = commit_gateway or AuthorityCommitGateway()

    def process_approval(
        self,
        request: StallBreakerApprovalRequest,
        current_snapshot: DealershipSnapshotSchema,
        candidate_alternative: RecoveryAlternative,
        evaluation_time_utc: Optional[datetime] = None,
    ) -> CommitResult:
        """Executes OCC-checked commitment of a StallBreaker recovery recommendation."""
        now = evaluation_time_utc or datetime.now(timezone.utc)

        # 1. State Version Validation (OCC Guard)
        if request.expected_snapshot_hash != current_snapshot.snapshot_hash:
            return CommitResult(
                status=CommitStatus.ABORTED_STALE_STATE,
                plan_id=request.plan_id,
                error_code="OCC_VERSION_MISMATCH",
                message=f"Dealership state mutated during review: expected '{request.expected_snapshot_hash}', actual '{current_snapshot.snapshot_hash}'.",
                expected_hash=request.expected_snapshot_hash,
                current_hash=current_snapshot.snapshot_hash,
                outbox_events_dispatched=0,
            )

        # 2. Construct Manager Approval Record
        approval = ManagerRecoveryApproval(
            plan_id=request.plan_id,
            snapshot_hash=current_snapshot.snapshot_hash or "",
            approver_id=request.approver_id,
            approved_freight_usd=request.approved_freight_usd or Decimal("50.00"),
            valid_until=now.replace(hour=23, minute=59, second=59),
        )

        commit_req = CommitRequest(
            plan_id=request.plan_id,
            expected_snapshot_hash=request.expected_snapshot_hash,
            approver_id=request.approver_id,
            approved_freight_usd=request.approved_freight_usd,
            approval_notes=request.approval_notes or f"Approved StallBreaker recovery for event '{request.event_id}'.",
        )

        return self.gateway.commit_recovery_plan(
            request=commit_req,
            current_snapshot=current_snapshot,
            candidate_alternative=candidate_alternative,
            approval=approval,
            evaluation_time_utc=now,
        )


# Global singleton instance
stallbreaker_approval_gateway = StallBreakerApprovalGateway()
