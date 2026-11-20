"""Golden End-to-End Benchmark Test for Scenario S-MATH-01.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md (Section 2.3, 2.4)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md

Provisional Benchmark Physical Timeline:
- Disrupted RO: RO-104 (Transmission Solenoid) on BAY-01 (HEAVY_DIAGNOSTIC_LIFT).
- Trigger: tick 159 (13:15 UTC).
- Unmitigated Baseline:
    * Primary ground delayed to tick 198.
    * RO-104 finishes at tick 222 (lateness = 30 ticks; w=3 => 90 weighted ticks; $225 penalty).
    * RO-106 cannot fit in horizon (222 + 2 + 24 = 248 > 228 overtime limit).
- Recovered Plan (Option S1 Hotshot):
    * Courier arrival usable ready tick: 165.
    * RO-104 finishes at tick 189 (promise tick 192 => 0 lateness).
    * Bay 01 freed at tick 189; vehicle move takes 2 ticks (189 -> 191).
    * RO-106 scheduled 191 -> 215 (promise tick 198 => 17 lateness; w=3 => 51 weighted ticks; $127.50 penalty).
    * Additional labor contribution: +$240.00 (RO-106 scheduled).
    * Alternative courier freight: $37.00.
    * Dual certification: PASS on L4 Sweep-Line + PASS on Supplemental Audit.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from app.authority.commit import AuthorityCommitGateway
from app.authority.models import (
    CommitRequest,
    CommitStatus,
    ManagerRecoveryApproval,
    OutboxEventType,
)
from app.optimise import OptimiseConfig
from app.recover.models import (
    DisruptionEvent,
    DisruptionType,
    RecoveryRecommendationReport,
)
from app.recover.replan import RecoveryReplanningPipeline
from app.schemas.domain import DealershipSnapshotSchema
from tests.test_optimise_audit_fixes import make_synthetic_evidence


class TestSMath01GoldenBenchmark:
    """End-to-end golden verification of S-MATH-01 recovery and dispatch commit."""

    def test_s_math_01_provisional_recovery_and_commit(
        self,
        validated_snapshot: DealershipSnapshotSchema,
    ):
        # 1. Prepare Disruption Event
        disruption = DisruptionEvent(
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            disruption_type=DisruptionType.PARTS_DELAY,
            trigger_tick=159,
            original_ready_tick=162,
            delayed_ready_tick=198,
            description="Supplier primary ground transit delayed 180 min to tick 198",
            event_timestamp_utc=datetime(2026, 11, 18, 13, 15, tzinfo=timezone.utc),
        )

        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)

        # 2. Execute Recovery Replanning Pipeline
        config = OptimiseConfig(allow_emergency_overtime=True)
        pipeline = RecoveryReplanningPipeline(config=config)

        report = pipeline.execute_recovery(
            snapshot=validated_snapshot,
            disruption_event=disruption,
            evidence=ev,
            evaluation_time_utc=datetime(2026, 11, 18, 13, 15, tzinfo=timezone.utc),
        )

        # 3. Assert Blast Radius Correctness
        assert report.blast_radius.disrupted_ro_id == "RO-104"
        assert report.blast_radius.is_immobilized_on_lift is True
        assert report.blast_radius.immobilized_bay_id == "BAY-01"
        assert "RO-106" in report.blast_radius.competing_ro_ids

        # 4. Assert Baseline Unmitigated State
        # In unmitigated baseline, RO-104 finishes at tick 222 (lateness = 30 ticks; w=3 => 90 weighted ticks)
        # and RO-106 is unschedulable within the 228-tick horizon
        assert report.baseline_weighted_lateness_ticks >= 90

        # 5. Assert S1 Hotshot Selection and Pareto Frontier
        assert report.recommended_option_id == "OFFER-104-S1"
        assert len(report.pareto_frontier) >= 1

        recommended = next(a for a in report.alternatives if a.option_id == "OFFER-104-S1")
        assert recommended.is_recommended is True
        assert recommended.sourcing_cost_usd == Decimal("37.00")

        # 6. Assert Physical Timelines of Recovered Plan
        rec_plan = recommended.schedule_result.plan
        ro104_assignments = [a for a in rec_plan.assignments if a.ro_id == "RO-104"]
        ro106_assignments = [a for a in rec_plan.assignments if a.ro_id == "RO-106"]

        assert len(ro104_assignments) > 0, "RO-104 must be scheduled"
        assert len(ro106_assignments) > 0, "RO-106 must be rescued and scheduled on freed BAY-01"

        # RO-104 finishes by tick 189
        ro104_finish = max(a.end_tick for a in ro104_assignments)
        assert ro104_finish <= 189, f"RO-104 finish tick ({ro104_finish}) exceeded 189"

        # RO-106 enters BAY-01 after vehicle move and completes by tick 215
        ro106_start = min(a.start_tick for a in ro106_assignments)
        ro106_finish = max(a.end_tick for a in ro106_assignments)
        assert ro106_start >= 189, f"RO-106 start ({ro106_start}) precedes 189"
        assert ro106_finish <= 215, f"RO-106 finish ({ro106_finish}) exceeded tick 215"

        # Recovered weighted lateness matches provisional physical benchmark
        assert recommended.weighted_lateness_ticks in (45, 51)

        # 7. Dual Independent Certification
        assert recommended.is_verified is True
        assert recommended.is_fully_certified is True
        assert "CERTIFIED" in str(recommended.certification_status)

        # 8. Authority & OCC Commit Gateway Execution
        gateway = AuthorityCommitGateway()
        manager_approval = ManagerRecoveryApproval(
            plan_id=recommended.plan_id,
            snapshot_hash=validated_snapshot.snapshot_hash or "",
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=4),
        )

        commit_req = CommitRequest(
            plan_id=recommended.plan_id,
            expected_snapshot_hash=validated_snapshot.snapshot_hash or "",
            approver_id="MGR-MARCUS",
            approved_freight_usd=Decimal("50.00"),
        )

        commit_result = gateway.commit_recovery_plan(
            request=commit_req,
            current_snapshot=validated_snapshot,
            candidate_alternative=recommended,
            approval=manager_approval,
        )

        assert commit_result.status == CommitStatus.COMMITTED
        assert commit_result.plan_id == recommended.plan_id
        assert len(commit_result.outbox_events) >= 2

        event_types = {e.event_type for e in commit_result.outbox_events}
        assert OutboxEventType.DISPATCH_PLAN_COMMITTED in event_types
        assert OutboxEventType.SUPPLIER_ORDER_EXPEDITED in event_types
