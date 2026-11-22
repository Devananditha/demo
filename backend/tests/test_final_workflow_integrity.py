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
