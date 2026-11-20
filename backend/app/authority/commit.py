"""Authority & Commit Gateway with Optimistic Concurrency Control (OCC) and Transactional Outbox.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md (Section 2.4)
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4.2 & 6)
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.6)
- docs/12_VERIFICATION_AND_REVALIDATION.md
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import uuid

from app.authority.models import (
    CommitRequest,
    CommitResult,
    CommitStatus,
    ManagerRecoveryApproval,
    OutboxEvent,
    OutboxEventType,
)
from app.core.snapshot import compute_snapshot_hash_from_dict
from app.recover.models import RecoveryAlternative
from app.schemas.domain import DealershipSnapshotSchema


class AuthorityCommitGateway:
    """Manages manager approvals, optimistic concurrency revalidation, and transactional outbox events."""

    def __init__(self):
        # In-memory simulated commit ledger and outbox event store
        self._committed_plans: Dict[Tuple[str, str], CommitResult] = {}
        self._outbox_store: List[OutboxEvent] = []

    def commit_recovery_plan(
        self,
        request: CommitRequest,
        current_snapshot: DealershipSnapshotSchema,
        candidate_alternative: RecoveryAlternative,
        approval: Optional[ManagerRecoveryApproval] = None,
        evaluation_time_utc: Optional[datetime] = None,
    ) -> CommitResult:
        """Executes idempotent OCC revalidation and simulated local commit."""
        now = evaluation_time_utc or datetime.now(timezone.utc)
        commit_key = (request.plan_id, request.expected_snapshot_hash)

        # --------------------------------------------------------------------
        # 1. Idempotency Check
        # --------------------------------------------------------------------
        if commit_key in self._committed_plans:
            return self._committed_plans[commit_key]

        # --------------------------------------------------------------------
        # 2. Approver Identity & Authority Validation
        # --------------------------------------------------------------------
        if not request.approver_id or request.approver_id.strip() == "":
            return CommitResult(
                status=CommitStatus.REJECTED_UNAUTHORIZED,
                plan_id=request.plan_id,
                error_code="UNAUTHORIZED_COMMIT",
                message="Commit rejected: missing or invalid approver identifier.",
                expected_hash=request.expected_snapshot_hash,
            )

        # --------------------------------------------------------------------
        # 3. Certification & Feasibility Gate
        # --------------------------------------------------------------------
        if not (candidate_alternative.is_verified and candidate_alternative.is_fully_certified):
            return CommitResult(
                status=CommitStatus.REJECTED_UNCERTIFIED,
                plan_id=request.plan_id,
                error_code="C7_PLAN_NOT_CERTIFIED",
                message="Cannot commit plan that failed independent L4 or supplemental operational certification.",
                expected_hash=request.expected_snapshot_hash,
            )

        # --------------------------------------------------------------------
        # 4. Approval Object Integrity & Expiration Check (if provided)
        # --------------------------------------------------------------------
        if approval:
            if approval.approver_id != request.approver_id:
                return CommitResult(
                    status=CommitStatus.REJECTED_UNAUTHORIZED,
                    plan_id=request.plan_id,
                    error_code="APPROVER_MISMATCH",
                    message="Commit rejected: approver ID does not match manager approval record.",
                    expected_hash=request.expected_snapshot_hash,
                )
            if approval.plan_id != request.plan_id:
                return CommitResult(
                    status=CommitStatus.INVALID_REQUEST,
                    plan_id=request.plan_id,
                    error_code="PLAN_ID_MISMATCH",
                    message=f"Approval record is for plan '{approval.plan_id}', expected '{request.plan_id}'.",
                    expected_hash=request.expected_snapshot_hash,
                )
            if approval.valid_until:
                valid_until = approval.valid_until if approval.valid_until.tzinfo else approval.valid_until.replace(tzinfo=timezone.utc)
                if valid_until < now:
                    return CommitResult(
                        status=CommitStatus.REJECTED_EXPIRED,
                        plan_id=request.plan_id,
                        error_code="APPROVAL_EXPIRED",
                        message=f"Manager approval expired at {valid_until.isoformat()}.",
                        expected_hash=request.expected_snapshot_hash,
                    )

        # Check freight approval threshold
        freight = candidate_alternative.sourcing_cost_usd
        if freight > Decimal("0.00"):
            has_explicit_freight_auth = (
                (request.approved_freight_usd is not None and request.approved_freight_usd >= freight)
                or (approval and approval.approved_freight_usd is not None and approval.approved_freight_usd >= freight)
                or (request.approval_notes and f"${freight:.2f}" in request.approval_notes)
            )
            if not has_explicit_freight_auth and freight > Decimal("50.00"):
                return CommitResult(
                    status=CommitStatus.REJECTED_UNAUTHORIZED,
                    plan_id=request.plan_id,
                    error_code="UNAUTHORIZED_FREIGHT_SURCHARGE",
                    message=f"Expedited freight (${freight:.2f}) exceeds $50.00 threshold without explicit approved amount.",
                    expected_hash=request.expected_snapshot_hash,
                )

        # --------------------------------------------------------------------
        # 5. Optimistic Concurrency Control (OCC) Fresh State Revalidation
        # --------------------------------------------------------------------
        actual_hash = current_snapshot.snapshot_hash
        if not actual_hash:
            actual_hash = compute_snapshot_hash_from_dict(current_snapshot.model_dump(mode="json"))

        if request.expected_snapshot_hash != actual_hash:
            return CommitResult(
                status=CommitStatus.ABORTED_STALE_STATE,
                plan_id=request.plan_id,
                error_code="OCC_VERSION_MISMATCH",
                message="Dealership state changed while reviewing proposal. Commit rejected.",
                expected_hash=request.expected_snapshot_hash,
                current_hash=actual_hash,
                outbox_events_dispatched=0,
            )

        # --------------------------------------------------------------------
        # 6. Transactional Outbox Event Generation
        # --------------------------------------------------------------------
        outbox_events = self._generate_outbox_events(
            request=request,
            snapshot=current_snapshot,
            candidate=candidate_alternative,
            now=now,
        )

        for event in outbox_events:
            self._outbox_store.append(event)

        result = CommitResult(
            status=CommitStatus.COMMITTED,
            plan_id=request.plan_id,
            committed_at=now,
            expected_hash=request.expected_snapshot_hash,
            current_hash=actual_hash,
            outbox_events_dispatched=len(outbox_events),
            outbox_events=outbox_events,
        )

        # Save to idempotent ledger
        self._committed_plans[commit_key] = result
        return result

    def _generate_outbox_events(
        self,
        request: CommitRequest,
        snapshot: DealershipSnapshotSchema,
        candidate: RecoveryAlternative,
        now: datetime,
    ) -> List[OutboxEvent]:
        """Generates transactional outbox event payloads for asynchronous dispatch."""
        events: List[OutboxEvent] = []

        # 1. DISPATCH_PLAN_COMMITTED
        plan = candidate.schedule_result.plan
        events.append(
            OutboxEvent(
                event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                aggregate_type="SCHEDULE_PLAN",
                aggregate_id=plan.plan_id,
                event_type=OutboxEventType.DISPATCH_PLAN_COMMITTED,
                payload={
                    "plan_id": plan.plan_id,
                    "rooftop_id": snapshot.rooftop.rooftop_id,
                    "snapshot_hash": snapshot.snapshot_hash,
                    "assignments_count": len(plan.assignments),
                    "gross_contribution_usd": str(candidate.gross_contribution_usd),
                    "net_objective_usd": str(candidate.net_objective_usd),
                    "committed_by": request.approver_id,
                    "committed_at": now.isoformat(),
                },
                created_at=now,
            )
        )

        # 2. SUPPLIER_ORDER_EXPEDITED (if alternative sourcing is expedited)
        sourcing = candidate.sourcing_candidate
        if sourcing.freight_surcharge_usd > Decimal("0.00") or sourcing.supplier_id.startswith("S1"):
            events.append(
                OutboxEvent(
                    event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                    aggregate_type="SUPPLIER_ORDER",
                    aggregate_id=sourcing.offer_id,
                    event_type=OutboxEventType.SUPPLIER_ORDER_EXPEDITED,
                    payload={
                        "offer_id": sourcing.offer_id,
                        "part_req_id": sourcing.part_req_id,
                        "supplier_id": sourcing.supplier_id,
                        "freight_surcharge_usd": str(sourcing.freight_surcharge_usd),
                        "usable_ready_tick": sourcing.usable_ready_tick,
                        "approved_by": request.approver_id,
                        "approved_at": now.isoformat(),
                    },
                    created_at=now,
                )
            )

        # 3. VEHICLE_MOVEMENT_DISPATCHED (for scheduled holding vehicle transports)
        for move in candidate.schedule_result.planned_movements:
            events.append(
                OutboxEvent(
                    event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                    aggregate_type="VEHICLE_MOVEMENT",
                    aggregate_id=move.vehicle_id,
                    event_type=OutboxEventType.VEHICLE_MOVEMENT_DISPATCHED,
                    payload={
                        "vehicle_id": move.vehicle_id,
                        "ro_id": move.ro_id,
                        "target_bay_id": move.target_bay_id,
                        "start_tick": move.start_tick,
                        "end_tick": move.end_tick,
                        "assigned_resource_id": move.assigned_resource_id,
                        "resource_type": move.resource_type,
                    },
                    created_at=now,
                )
            )

        return events

    def get_dispatched_outbox_events(self) -> List[OutboxEvent]:
        """Returns all simulated outbox events recorded in memory."""
        return list(self._outbox_store)

    def get_outbox_events(self) -> List[OutboxEvent]:
        """Alias for get_dispatched_outbox_events."""
        return self.get_dispatched_outbox_events()

    def get_ledger_entry(self, plan_id: str, expected_snapshot_hash: str) -> Optional[CommitResult]:
        """Retrieves a committed plan entry from the idempotent ledger."""
        return self._committed_plans.get((plan_id, expected_snapshot_hash))
