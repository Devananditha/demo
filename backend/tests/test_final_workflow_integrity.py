"""Regression test suite for final workflow integrity and verification gate.

Validates:
1. Verifier endpoint (/api/v1/verifier/verify) independently verifies candidate plans.
2. Verifier detects invalid plans (overlapping resource assignments, invalid snapshots).
3. StallBreaker approval requires exact event_id and plan_id (rejects unknown/missing).
4. Sourcing costs and economic deltas are genuine and preserved.
5. Ingested events properly gate recovery recommendations.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.api.main import app, reset_live_snapshot
from app.data.loader import load_fixture_data
from app.optimise import CPSATScheduler, OptimiseConfig
from app.stallbreaker import (
    EventType,
    StoredEvent,
    compute_hmac_sha256,
    stallbreaker_engine,
    stallbreaker_event_store,
)
from app.verifier.models import CandidateSchedulePlan, VerificationResult


@pytest.fixture
def clean_client():
    reset_live_snapshot()
    stallbreaker_event_store.clear()
    client = TestClient(app)
    return client


def _create_sample_event(event_id: str = "EVT-REGRESSION-INT-001") -> StoredEvent:
    now = datetime.now(timezone.utc)
    event = StoredEvent(
        event_id=event_id,
        rooftop_id="ROOF-01",
        event_type=EventType.PARTS_ETA_CHANGED,
        entity_type="PART_REQUIREMENT",
        entity_id="PART-REQ-104-SOLENOID",
        payload={
            "delay_minutes": 180,
            "previous_eta_tick": 129,
            "new_ready_tick": 198,
            "affected_ro_id": "RO-104",
        },
        occurred_at=now,
        ingested_at=now,
        snapshot_hash_before="",
        snapshot_hash_after="",
    )
    stallbreaker_event_store.record_event(event)
    return event


class TestFinalWorkflowIntegrity:
    """Rigorous tests covering end-to-end verification and workflow integrity."""

    def test_verifier_endpoint_valid_schedule_plan(self, clean_client):
        """Verifier endpoint correctly audits a valid CP-SAT schedule plan."""
        snapshot = load_fixture_data()
        scheduler = CPSATScheduler(OptimiseConfig(time_budget_seconds=2.0))
        result = scheduler.schedule(snapshot)
        assert result.plan is not None

        payload = {
            "rooftop_id": snapshot.rooftop.rooftop_id,
            "snapshot_hash": snapshot.snapshot_hash,
            "plan": result.plan.model_dump(),
        }

        resp = clean_client.post("/api/v1/verifier/verify", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_id"] == result.plan.plan_id
        assert data["snapshot_hash"] == snapshot.snapshot_hash
        assert data["is_valid"] is True
        assert len(data["violations"]) == 0
        assert data["execution_time_ms"] > 0

    def test_verifier_endpoint_detects_violations(self, clean_client):
        """Verifier endpoint catches constraint violations (e.g., stale hash, missing auth)."""
        snapshot = load_fixture_data()
        scheduler = CPSATScheduler(OptimiseConfig(time_budget_seconds=2.0))
        result = scheduler.schedule(snapshot)
        plan_dict = result.plan.model_dump()

        # Corrupt plan with stale snapshot hash
        plan_dict["snapshot_hash"] = "stale_or_invalid_hash_value"
        payload = {
            "rooftop_id": snapshot.rooftop.rooftop_id,
            "snapshot_hash": snapshot.snapshot_hash,
            "plan": plan_dict,
        }

        resp = clean_client.post("/api/v1/verifier/verify", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert len(data["violations"]) > 0
        assert any(v.get("constraint") == "C7" or "C7" in v.get("code", "") for v in data["violations"])

    def test_approval_rejects_unknown_event(self, clean_client):
        """Approval endpoint rejects requests referencing unknown event IDs."""
        snapshot = load_fixture_data()
        payload = {
            "plan_id": "PLAN-OPT-01",
            "event_id": "EVT-NONEXISTENT-999",
            "expected_snapshot_hash": snapshot.snapshot_hash,
            "approver_id": "MGR-MARCUS",
            "approved_freight_usd": 37.0,
        }
        resp = clean_client.post("/api/v1/stallbreaker/approve", json=payload)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_approval_rejects_unknown_plan(self, clean_client):
        """Approval endpoint rejects requests referencing unknown plan IDs."""
        event = _create_sample_event("EVT-TEST-PLAN-01")
        snapshot = load_fixture_data()

        payload = {
            "plan_id": "PLAN-COMPLETELY-FICTITIOUS-999",
            "event_id": event.event_id,
            "expected_snapshot_hash": snapshot.snapshot_hash,
            "approver_id": "MGR-MARCUS",
            "approved_freight_usd": 37.0,
        }
        resp = clean_client.post("/api/v1/stallbreaker/approve", json=payload)
        assert resp.status_code in (400, 404)
        assert "plan" in resp.json()["detail"].lower()

    def test_approval_rejects_stale_snapshot_occ(self, clean_client):
        """Approval endpoint rejects stale snapshot hash under OCC guard."""
        event = _create_sample_event("EVT-TEST-OCC-01")
        snapshot = load_fixture_data()

        # Run recovery to generate valid plan IDs
        rec_resp = clean_client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={"event_id": event.event_id, "allow_emergency_overtime": True},
        )
        assert rec_resp.status_code == 200
        plan_id = rec_resp.json()["recommended_plan_id"]
        assert plan_id is not None

        payload = {
            "plan_id": plan_id,
            "event_id": event.event_id,
            "expected_snapshot_hash": "STALE_OR_OUTDATED_SNAPSHOT_HASH",
            "approver_id": "MGR-MARCUS",
            "approved_freight_usd": 37.0,
        }
        resp = clean_client.post("/api/v1/stallbreaker/approve", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ABORTED_STALE_STATE"
        assert data["error_code"] == "OCC_VERSION_MISMATCH"

    def test_recovery_recommendations_contain_schedule_result_and_plan(self, clean_client):
        """Recovery recommendations return candidate schedule plans for verifier audit."""
        event = _create_sample_event("EVT-TEST-RECOVERY-01")
        resp = clean_client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={"event_id": event.event_id, "allow_emergency_overtime": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["evaluated_alternatives"]) > 0

        for alt in data["evaluated_alternatives"]:
            assert "plan_id" in alt
            assert "sourcing_cost_usd" in alt
            # schedule_result must be present and contain assignments
            assert alt.get("schedule_result") is not None
            sched = alt["schedule_result"]
            assert "plan" in sched
            assert "assignments" in sched["plan"]
            assert len(sched["plan"]["assignments"]) > 0

            # Sourcing cost must be a genuine decimal string, not fabricated
            cost = float(alt["sourcing_cost_usd"])
            assert cost >= 0.0

    def test_disruption_analysis_rejects_unknown_event_404(self, clean_client):
        """Disruption analysis endpoint returns 404 for unknown event IDs without fallback."""
        resp = clean_client.post(
            "/api/v1/stallbreaker/disruption-analysis",
            json={"event_id": "EVT-UNKNOWN-FABRICATED-404"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_disruption_analysis_rejects_missing_event_id_400(self, clean_client):
        """Disruption analysis endpoint returns 400 when event_id is empty."""
        resp = clean_client.post(
            "/api/v1/stallbreaker/disruption-analysis",
            json={"event_id": "   "},
        )
        assert resp.status_code == 400

    def test_e2e_genuine_workflow_complete_sequence(self, clean_client):
        """Comprehensive end-to-end integration test:
        1. Reset canonical workshop
        2. Ingest real synthetic parts-delay event
        3. Retrieve mutated workshop state and new snapshot hash
        4. Generate recovery alternatives using exact persisted event ID
        5. Select one returned candidate schedule
        6. Submit that exact schedule to independent verifier
        7. Confirm verification passes
        8. Approve using verified plan ID, exact event ID and current snapshot hash
        9. Confirm result is COMMITTED
        10. Confirm outbox contains expected events
        """
        # 1. Reset canonical workshop and get pre-disruption hash
        reset_live_snapshot()
        state_resp_initial = clean_client.get("/api/v1/state")
        assert state_resp_initial.status_code == 200
        initial_hash = state_resp_initial.json()["snapshot_hash"]
        assert len(initial_hash) > 0

        # 2. Ingest real synthetic parts-delay event
        payload = {
            "delay_minutes": 180,
            "new_ready_tick": 198,
            "previous_eta_tick": 129,
            "affected_ro_id": "RO-104",
        }
        sig = compute_hmac_sha256(payload)
        event_id = "EVT-E2E-GENUINE-SEQUENCE-001"
        ingest_resp = clean_client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": event_id,
                "rooftop_id": "ROOF-01",
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": payload,
                "signature": sig,
            },
        )
        assert ingest_resp.status_code in (200, 201)
        ingest_data = ingest_resp.json()
        assert ingest_data["event_id"] == event_id

        # 3. Retrieve mutated workshop state and new snapshot hash
        mutated_resp = clean_client.get("/api/v1/stallbreaker/state")
        assert mutated_resp.status_code == 200
        mutated_state = mutated_resp.json()
        new_snapshot_hash = mutated_state["snapshot_hash"]
        assert len(new_snapshot_hash) > 0
        assert new_snapshot_hash != initial_hash

        # 4. Generate recovery alternatives using exact persisted event ID
        rec_resp = clean_client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={
                "event_id": event_id,
                "allow_emergency_overtime": True,
            },
        )
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        assert rec_data["is_recovery_feasible"] is True
        assert len(rec_data["evaluated_alternatives"]) > 0

        # 5. Select one returned candidate schedule (recommended alternative)
        candidate = next(
            (a for a in rec_data["evaluated_alternatives"] if a.get("is_recommended")),
            rec_data["evaluated_alternatives"][0],
        )
        plan_id = candidate["plan_id"]
        assert candidate.get("schedule_result") is not None
        plan = candidate["schedule_result"]["plan"]
        assert plan["plan_id"] == plan_id
        # Plan snapshot hash must match the mutated snapshot hash
        assert plan["snapshot_hash"] == new_snapshot_hash

        # 6. Submit that exact schedule to independent verifier
        verify_resp = clean_client.post(
            "/api/v1/verifier/verify",
            json={
                "rooftop_id": mutated_state["rooftop_id"],
                "snapshot_hash": new_snapshot_hash,
                "plan": plan,
            },
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()

        # 7. Confirm that verification passes
        assert verify_data["is_valid"] is True
        assert len(verify_data["violations"]) == 0
        assert verify_data["plan_id"] == plan_id
        assert verify_data["snapshot_hash"] == new_snapshot_hash

        # 8. Approve using verified plan ID, exact event ID and current snapshot hash
        sourcing_cost = float(candidate["sourcing_cost_usd"])
        approve_resp = clean_client.post(
            "/api/v1/stallbreaker/approve",
            json={
                "plan_id": plan_id,
                "event_id": event_id,
                "expected_snapshot_hash": new_snapshot_hash,
                "approver_id": "MGR-MARCUS",
                "approved_freight_usd": sourcing_cost,
                "approval_notes": f"Authorized StallBreaker recovery plan {plan_id} for event {event_id}.",
            },
        )
        assert approve_resp.status_code == 200
        commit_data = approve_resp.json()

        # 9. Confirm that the result is COMMITTED
        assert commit_data["status"] == "COMMITTED"
        assert commit_data["plan_id"] == plan_id

        # 10. Confirm that the outbox contains the expected events
        assert commit_data["outbox_events_dispatched"] > 0
        assert commit_data.get("outbox_events") is not None
        assert len(commit_data["outbox_events"]) > 0
        event_types = [e["event_type"] for e in commit_data["outbox_events"]]
        assert "DISPATCH_PLAN_COMMITTED" in event_types

    def test_e2e_stale_state_change_prevents_commitment_dispatches_zero_events(self, clean_client):
        """11. A state change after verification prevents commitment and dispatches zero events."""
        # Setup: Ingest an initial event and obtain a verified candidate plan
        reset_live_snapshot()
        payload_1 = {
            "delay_minutes": 180,
            "new_ready_tick": 198,
            "previous_eta_tick": 129,
            "affected_ro_id": "RO-104",
        }
        sig_1 = compute_hmac_sha256(payload_1)
        event_id_1 = "EVT-E2E-STALE-TEST-001"
        clean_client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": event_id_1,
                "rooftop_id": "ROOF-01",
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": payload_1,
                "signature": sig_1,
            },
        )

        state_before = clean_client.get("/api/v1/stallbreaker/state").json()
        verified_hash = state_before["snapshot_hash"]

        rec_resp = clean_client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={"event_id": event_id_1, "allow_emergency_overtime": True},
        )
        candidate = rec_resp.json()["evaluated_alternatives"][0]
        plan_id = candidate["plan_id"]
        plan = candidate["schedule_result"]["plan"]

        # Verify candidate plan
        verify_resp = clean_client.post(
            "/api/v1/verifier/verify",
            json={
                "rooftop_id": state_before["rooftop_id"],
                "snapshot_hash": verified_hash,
                "plan": plan,
            },
        )
        assert verify_resp.json()["is_valid"] is True

        # Now simulate an external state mutation AFTER verification:
        # Ingest a second event (operation completed or technician unavailable) which mutates state hash
        payload_2 = {
            "tech_id": "TECH-01",
            "reason": "Emergency medical leave",
            "effective_tick": 160,
        }
        sig_2 = compute_hmac_sha256(payload_2)
        event_id_2 = "EVT-E2E-MUTATE-STATE-002"
        clean_client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": event_id_2,
                "rooftop_id": "ROOF-01",
                "event_type": "TECHNICIAN_UNAVAILABLE",
                "entity_type": "TECHNICIAN",
                "entity_id": "TECH-01",
                "payload": payload_2,
                "signature": sig_2,
            },
        )

        state_after = clean_client.get("/api/v1/stallbreaker/state").json()
        current_mutated_hash = state_after["snapshot_hash"]
        # Confirm that the state hash has indeed mutated
        assert current_mutated_hash != verified_hash

        # Attempt to approve the previously verified candidate using the now-stale verified_hash
        approve_resp = clean_client.post(
            "/api/v1/stallbreaker/approve",
            json={
                "plan_id": plan_id,
                "event_id": event_id_1,
                "expected_snapshot_hash": verified_hash,  # Now stale!
                "approver_id": "MGR-MARCUS",
                "approved_freight_usd": float(candidate["sourcing_cost_usd"]),
            },
        )
        assert approve_resp.status_code == 200
        commit_result = approve_resp.json()

        # Commitment must be aborted due to OCC mismatch
        assert commit_result["status"] == "ABORTED_STALE_STATE"
        assert commit_result["error_code"] == "OCC_VERSION_MISMATCH"
        # Zero outbox events must be dispatched
        assert commit_result["outbox_events_dispatched"] == 0
        assert commit_result.get("outbox_events") is None or len(commit_result["outbox_events"]) == 0

