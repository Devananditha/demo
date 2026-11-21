"""Comprehensive End-to-End Adversarial Verification & Hardening Test Suite.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md
- docs/12_VERIFICATION_AND_REVALIDATION.md

Guarantees Verified:
1. PARTS_ETA_CHANGED mutates live snapshot.
2. Subsequent /api/v1/recover/replan and /api/v1/predict/readiness reflect mutated ETA.
3. Recovery plan certified by L4 Sweep-Line Oracle.
4. Decision Replay diff and explainability recorded.
5. Stale OCC manager approval aborted (OCC_VERSION_MISMATCH).
6. Process restart test (in-memory cache cleared, re-instantiated StallBreakerEventStore re-hydrates from DB).
7. Objective accounting identically matches CP-SAT terms.
8. Null-control produces zero artificial lift (Delta Z == $0.00).
9. Production mode rejects unsigned events; tampered payloads rejected.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import uuid
import pytest
from fastapi.testclient import TestClient

from app.api.main import app, get_live_snapshot, reset_live_snapshot
from app.benchmark.models import BenchmarkScenarioType, DispatchMethod
from app.benchmark.runner import benchmark_runner
from app.data.loader import load_canonical_evidence, load_fixture_data
from app.optimise.accounting import compute_net_economic_objective
from app.schemas.domain import DealershipSnapshotSchema, ROStatus
from app.stallbreaker import (
    EventIngestRequest,
    EventType,
    StallBreakerEventStore,
    compute_hmac_sha256,
    stallbreaker_event_store,
)
from app.verifier.sweep_oracle import SweepLineOracle


@pytest.fixture(autouse=True)
def reset_state():
    """Resets the live snapshot and in-memory event store before each test."""
    reset_live_snapshot()
    yield
    reset_live_snapshot()


@pytest.fixture
def client():
    return TestClient(app)


class TestE2EVerificationFlow:
    """Verifies complete end-to-end event-to-recovery pipeline and security properties."""

    def test_property_1_and_2_event_mutation_propagates_to_downstream_apis(self, client: TestClient):
        """1 & 2: PARTS_ETA_CHANGED mutates live snapshot; replan & readiness reflect mutated state."""
        snap_initial = get_live_snapshot()
        initial_hash = snap_initial.snapshot_hash
        assert initial_hash is not None

        # 1. Ingest PARTS_ETA_CHANGED event with unique event ID
        event_id = f"EVT-E2E-MUTATE-{uuid.uuid4().hex[:8]}"
        payload = {
            "part_req_id": "PART-REQ-104-SOLENOID",
            "new_ready_tick": 198,
            "delay_minutes": 180,
        }
        sig = compute_hmac_sha256(payload)
        now = datetime.now(timezone.utc)

        resp = client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": event_id,
                "rooftop_id": snap_initial.rooftop.rooftop_id,
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": payload,
                "occurred_at": now.isoformat(),
                "signature": sig,
            },
        )
        assert resp.status_code == 201
        ingest_data = resp.json()
        assert ingest_data["status"] == "ACCEPTED"
        assert ingest_data["requires_recovery"] is True
        mutated_hash = ingest_data["new_snapshot_hash"]
        assert mutated_hash != initial_hash

        # Verify /api/v1/state returns the mutated snapshot hash
        state_resp = client.get("/api/v1/state")
        assert state_resp.status_code == 200
        assert state_resp.json()["snapshot_hash"] == mutated_hash

        # 2. Subsequent /api/v1/predict/readiness uses mutated state
        readiness_resp = client.post(
            "/api/v1/predict/readiness",
            json={
                "rooftop_id": snap_initial.rooftop.rooftop_id,
                "snapshot_hash": mutated_hash,
            },
        )
        assert readiness_resp.status_code == 200
        readiness_data = readiness_resp.json()
        ro_104_assessment = next(
            (c for c in readiness_data["assessments"] if c["ro_id"] == "RO-104"), None
        )
        assert ro_104_assessment is not None
        assert ro_104_assessment["state"] in ("AT_RISK", "BLOCKED")

        # 3. Subsequent /api/v1/recover/replan operates on mutated state
        replan_resp = client.post(
            "/api/v1/recover/replan",
            json={
                "rooftop_id": snap_initial.rooftop.rooftop_id,
                "snapshot_hash": mutated_hash,
                "allow_emergency_overtime": True,
            },
        )
        assert replan_resp.status_code == 200
        replan_data = replan_resp.json()
        assert len(replan_data["alternatives"]) > 0

    def test_property_3_and_4_recovery_plan_verified_and_replay_recorded(self, client: TestClient):
        """3 & 4: Recovery plan is certified by L4 Oracle; Decision Replay diff and explainability recorded."""
        snap = get_live_snapshot()

        rec_resp = client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={"allow_emergency_overtime": True},
        )
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        assert rec_data["is_recovery_feasible"] is True

        # Property 3: Verify plan is certified by L4 sweep-line oracle in replan report
        recommended_alt = next((a for a in rec_data["evaluated_alternatives"] if a["is_recommended"]), None)
        assert recommended_alt is not None
        assert recommended_alt["schedule_result"]["is_verified"] is True
        assert recommended_alt["schedule_result"]["is_fully_certified"] is True

        # Also verify baseline schedule plan against current state via /api/v1/verifier/verify
        opt_resp = client.post(
            "/api/v1/optimise/schedule",
            json={
                "rooftop_id": snap.rooftop.rooftop_id,
                "snapshot_hash": snap.snapshot_hash,
                "allow_emergency_overtime": True,
            },
        )
        assert opt_resp.status_code == 200
        opt_plan = opt_resp.json()["plan"]

        verify_resp = client.post(
            "/api/v1/verifier/verify",
            json={
                "rooftop_id": snap.rooftop.rooftop_id,
                "snapshot_hash": snap.snapshot_hash,
                "plan": opt_plan,
            },
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["is_valid"] is True
        assert len(verify_data["violations"]) == 0

        # Property 4: Decision Replay diff & explainability recorded
        replay = rec_data["decision_replay"]
        assert replay is not None
        assert float(replay["net_economic_delta_usd"]) > 0.0
        assert float(replay["sourcing_freight_usd"]) == 37.00
        assert rec_data["explainability"] is not None
        assert "RO-104" in rec_data["explainability"]["recommendation_summary"]

    def test_property_5_stale_occ_approval_aborted(self, client: TestClient):
        """5: Manager approval with stale OCC version is aborted."""
        snap_initial = get_live_snapshot()

        # Attempt approval committing with stale_hash
        approve_resp = client.post(
            "/api/v1/stallbreaker/approve",
            json={
                "plan_id": "PLAN-REC-OFFER-104-S1",
                "event_id": f"EVT-APPROVE-STALE-{uuid.uuid4().hex[:8]}",
                "expected_snapshot_hash": "STALE-HASH-INCORRECT-OCC-VERSION",
                "approver_id": "MGR-MARCUS",
                "approved_freight_usd": "50.00",
            },
        )
        assert approve_resp.status_code == 200
        approve_data = approve_resp.json()
        assert approve_data["status"] == "ABORTED_STALE_STATE"
        assert approve_data["error_code"] == "OCC_VERSION_MISMATCH"

    def test_property_6_database_event_hydration_across_process_restart(self):
        """6: Events persist in DB; a re-instantiated StallBreakerEventStore re-hydrates them."""
        # 1. Record an event in the current store
        now = datetime.now(timezone.utc)
        test_event_id = f"EVT-RESTART-{int(now.timestamp())}"
        from app.stallbreaker.models import StoredEvent
        evt = StoredEvent(
            event_id=test_event_id,
            rooftop_id="ROOF-01",
            event_type=EventType.PARTS_ETA_CHANGED,
            entity_type="PART_REQUIREMENT",
            entity_id="PART-REQ-104-SOLENOID",
            payload={"delay_minutes": 180, "new_ready_tick": 198},
            occurred_at=now,
            ingested_at=now,
            snapshot_hash_before="HASH-PRE",
            snapshot_hash_after="HASH-POST",
        )
        stallbreaker_event_store.record_event(evt)
        assert stallbreaker_event_store.get_event(test_event_id) is not None

        # 2. Simulate process restart: create a new EventStore instance with auto_init_db=True
        restarted_store = StallBreakerEventStore(auto_init_db=True)
        # Verify event was loaded from SQLite database into memory
        loaded_evt = restarted_store.get_event(test_event_id)
        assert loaded_evt is not None
        assert loaded_evt.event_id == test_event_id
        assert loaded_evt.snapshot_hash_before == "HASH-PRE"
        assert loaded_evt.snapshot_hash_after == "HASH-POST"

    def test_property_7_objective_accounting_matches_cpsat_terms(self):
        """7: Objective accounting identically matches CP-SAT terms (Gross - Lateness - Sourcing - Bay - Churn)."""
        gross = Decimal("780.00")
        lateness = Decimal("255.00")
        sourcing = Decimal("37.00")
        bay_blocked = Decimal("10.00")
        churn = Decimal("5.00")

        expected_z = gross - lateness - sourcing - bay_blocked - churn
        computed_z = compute_net_economic_objective(
            gross_contribution_usd=gross,
            lateness_penalty_usd=lateness,
            sourcing_cost_usd=sourcing,
            bay_blocked_cost_usd=bay_blocked,
            churn_cost_usd=churn,
        )
        assert computed_z == expected_z.quantize(Decimal("0.01"))
        assert computed_z == Decimal("473.00")

    def test_property_8_null_control_produces_zero_artificial_lift(self):
        """8: Null-control produces zero artificial lift (Delta Z == $0.00) and zero churn."""
        res = benchmark_runner.run_scenario(BenchmarkScenarioType.NULL_CONTROL, seed=42)
        assert res.stallbreaker_advantage_usd == Decimal("0.00")
        assert res.methods[DispatchMethod.STALLBREAKER.value].recovery_plan_churn == 0
        assert res.methods[DispatchMethod.STALLBREAKER.value].constraint_violations == 0

        # Run under distinct seed as well
        res_777 = benchmark_runner.run_scenario(BenchmarkScenarioType.NULL_CONTROL, seed=777)
        assert res_777.stallbreaker_advantage_usd == Decimal("0.00")
        assert res_777.methods[DispatchMethod.STALLBREAKER.value].recovery_plan_churn == 0

    def test_property_9_security_production_hmac_and_timestamp_freshness(self, client: TestClient, monkeypatch):
        """9: Production mode rejects unsigned events; tampered payloads and stale timestamps rejected."""
        snap = get_live_snapshot()
        payload = {"part_req_id": "PART-REQ-104-SOLENOID", "new_ready_tick": 198}
        valid_sig = compute_hmac_sha256(payload)

        # 9a. In production mode, unsigned event is rejected with 401
        monkeypatch.setenv("REQUIRE_HMAC", "true")
        resp_unsigned = client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": "EVT-SEC-UNSIGNED",
                "rooftop_id": snap.rooftop.rooftop_id,
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": payload,
                # signature omitted
            },
        )
        assert resp_unsigned.status_code == 401
        assert "signature required" in resp_unsigned.json()["detail"].lower()

        # 9b. Tampered payload with mismatched signature rejected with 401
        tampered_payload = {"part_req_id": "PART-REQ-104-SOLENOID", "new_ready_tick": 199}
        resp_tampered = client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": "EVT-SEC-TAMPERED",
                "rooftop_id": snap.rooftop.rooftop_id,
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": tampered_payload,
                "signature": valid_sig,  # signature was for ready_tick=198
            },
        )
        assert resp_tampered.status_code == 401
        assert "Invalid HMAC-SHA256" in resp_tampered.json()["detail"]

        # 9c. Stale timestamp (skew > 300 seconds) rejected with 400
        monkeypatch.delenv("REQUIRE_HMAC", raising=False)
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=600)
        resp_stale = client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": "EVT-SEC-STALE",
                "rooftop_id": snap.rooftop.rooftop_id,
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": payload,
                "occurred_at": stale_time.isoformat(),
            },
        )
        assert resp_stale.status_code == 400
        assert "Stale or future event timestamp" in resp_stale.json()["detail"]
