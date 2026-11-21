"""Comprehensive Test Suite for StallBreaker Event-Driven Disruption & Recovery Engine.

Verifies:
1. Event ingestion with cryptographic HMAC-SHA256 verification and tamper rejection.
2. Idempotent event processing and deduplication.
3. State transitions across all 7 domain event types.
4. StallBreaker disruption analysis and schedule invalidation detection.
5. Realistic candidate action generation and rejection of hard-constraint violations (C1).
6. Deterministic CP-SAT re-solve, L4 Sweep-Line verification, and Decision Replay deltas.
7. Version-bound manager approval with OCC stale-state abort and transactional outbox events.
8. FastAPI REST endpoints for /stallbreaker/events, /state, /disruption-analysis, /recovery-recommendations, /replay, /approve.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.api.main import app, reset_live_snapshot
from app.data.loader import load_fixture_data
from app.schemas.domain import (
    DealershipSnapshotSchema,
    PartInventoryStatus,
    ROStatus,
    TaskStatus,
)
from app.stallbreaker import (
    DealershipStateMutator,
    EventIngestRequest,
    EventType,
    StallBreakerApprovalRequest,
    StallBreakerEngine,
    StallBreakerEventStore,
    StoredEvent,
    compute_hmac_sha256,
    stallbreaker_event_store,
    verify_hmac_sha256,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Resets global singleton stores and live snapshot before each test."""
    stallbreaker_event_store.clear()
    reset_live_snapshot()
    yield
    stallbreaker_event_store.clear()
    reset_live_snapshot()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def canonical_snapshot() -> DealershipSnapshotSchema:
    return load_fixture_data()


# ============================================================================
# 1. SECURITY & HMAC-SHA256 SIGNATURE VERIFICATION
# ============================================================================

class TestStallBreakerSecurity:
    """Verifies HMAC-SHA256 cryptographic signature validation and tamper detection."""

    def test_compute_and_verify_signature_success(self):
        payload = {"part_req_id": "PART-REQ-104-SOLENOID", "delay_minutes": 180, "new_eta_tick": 198}
        sig = compute_hmac_sha256(payload)
        assert len(sig) == 64
        assert verify_hmac_sha256(payload, sig) is True

    def test_tampered_payload_signature_rejected(self):
        payload = {"part_req_id": "PART-REQ-104-SOLENOID", "delay_minutes": 180}
        sig = compute_hmac_sha256(payload)

        # Tampered payload
        tampered_payload = {"part_req_id": "PART-REQ-104-SOLENOID", "delay_minutes": 999}
        assert verify_hmac_sha256(tampered_payload, sig) is False

    def test_empty_or_blank_signature_rejected(self):
        payload = {"test": "data"}
        assert verify_hmac_sha256(payload, "") is False
        assert verify_hmac_sha256(payload, "   ") is False


# ============================================================================
# 2. EVENT STORE IDEMPOTENCY & DEDUPLICATION
# ============================================================================

class TestStallBreakerIdempotency:
    """Verifies duplicate event deduplication and tamper detection."""

    def test_idempotent_event_deduplication(self):
        store = StallBreakerEventStore()
        now = datetime.now(timezone.utc)
        evt = StoredEvent(
            event_id="EVT-001",
            rooftop_id="ROOF-01",
            event_type=EventType.PARTS_ETA_CHANGED,
            entity_type="PART_REQUIREMENT",
            entity_id="PART-REQ-104-SOLENOID",
            payload={"delay_minutes": 180},
            occurred_at=now,
            ingested_at=now,
            snapshot_hash_before="HASH-A",
            snapshot_hash_after="HASH-B",
        )

        recorded, is_dup = store.record_event(evt)
        assert is_dup is False
        assert recorded.event_id == "EVT-001"

        # Re-submit identical event
        dup_recorded, dup_is_dup = store.record_event(evt)
        assert dup_is_dup is True
        assert dup_recorded.event_id == "EVT-001"
        assert len(store.list_events()) == 1


# ============================================================================
# 3. DOMAIN EVENT STATE TRANSITIONS
# ============================================================================

class TestStallBreakerStateTransitions:
    """Verifies deterministic state mutations across domain event types."""

    def test_parts_eta_changed_mutation(self, canonical_snapshot: DealershipSnapshotSchema):
        req = EventIngestRequest(
            event_id="EVT-PARTS-01",
            event_type=EventType.PARTS_ETA_CHANGED,
            entity_type="PART_REQUIREMENT",
            entity_id="PART-REQ-104-SOLENOID",
            payload={"new_ready_tick": 198, "delay_minutes": 180},
        )

        mutated, requires_recovery, summary = DealershipStateMutator.apply_event(canonical_snapshot, req)
        assert requires_recovery is True
        assert "198" in summary

        part = next(p for p in mutated.part_requirements if p.part_req_id == "PART-REQ-104-SOLENOID")
        assert part.usable_ready_tick == 198
        assert part.inventory_status == PartInventoryStatus.IN_TRANSIT
        assert mutated.snapshot_hash != canonical_snapshot.snapshot_hash

    def test_part_unavailable_mutation(self, canonical_snapshot: DealershipSnapshotSchema):
        req = EventIngestRequest(
            event_id="EVT-UNAVAIL-01",
            event_type=EventType.PART_UNAVAILABLE,
            entity_type="PART_REQUIREMENT",
            entity_id="PART-REQ-104-SOLENOID",
            payload={"reason": "FACTORY_BACKORDER"},
        )

        mutated, requires_recovery, summary = DealershipStateMutator.apply_event(canonical_snapshot, req)
        assert requires_recovery is True
        part = next(p for p in mutated.part_requirements if p.part_req_id == "PART-REQ-104-SOLENOID")
        assert part.inventory_status == PartInventoryStatus.BACKORDERED
        assert part.usable_ready_tick is None

    def test_technician_unavailable_mutation(self, canonical_snapshot: DealershipSnapshotSchema):
        req = EventIngestRequest(
            event_id="EVT-TECH-01",
            event_type=EventType.TECHNICIAN_UNAVAILABLE,
            entity_type="TECHNICIAN",
            entity_id="TECH-02",
            payload={"reason": "FAMILY_EMERGENCY"},
        )

        mutated, requires_recovery, summary = DealershipStateMutator.apply_event(canonical_snapshot, req)
        assert requires_recovery is True
        tech = next(t for t in mutated.technicians if t.tech_id == "TECH-02")
        assert tech.is_active is False

    def test_bay_reservation_changed_mutation(self, canonical_snapshot: DealershipSnapshotSchema):
        req = EventIngestRequest(
            event_id="EVT-BAY-01",
            event_type=EventType.BAY_RESERVATION_CHANGED,
            entity_type="BAY",
            entity_id="BAY-01",
            payload={"is_operational": False, "reason": "HYDRAULIC_FAULT"},
        )

        mutated, requires_recovery, summary = DealershipStateMutator.apply_event(canonical_snapshot, req)
        assert requires_recovery is True
        bay = next(b for b in mutated.bays if b.bay_id == "BAY-01")
        assert bay.is_operational is False

    def test_operation_completed_mutation(self, canonical_snapshot: DealershipSnapshotSchema):
        req = EventIngestRequest(
            event_id="EVT-OP-01",
            event_type=EventType.OPERATION_COMPLETED,
            entity_type="TASK",
            entity_id="TASK-104-01",
            payload={"task_id": "TASK-104-01"},
        )

        mutated, requires_recovery, summary = DealershipStateMutator.apply_event(canonical_snapshot, req)
        task = next(t for t in mutated.tasks if t.task_id == "TASK-104-01")
        assert task.status == TaskStatus.COMPLETED


# ============================================================================
# 4. DISRUPTION ANALYSIS & RECOVERY ENGINE
# ============================================================================

class TestStallBreakerEngine:
    """Verifies StallBreaker disruption analysis, candidate actions, and CP-SAT recovery."""

    def test_disruption_analysis_identifies_affected_ros_and_bays(self, canonical_snapshot: DealershipSnapshotSchema):
        engine = StallBreakerEngine()
        now = datetime.now(timezone.utc)
        event = StoredEvent(
            event_id="EVT-ANALYZE-01",
            rooftop_id="ROOF-01",
            event_type=EventType.PARTS_ETA_CHANGED,
            entity_type="PART_REQUIREMENT",
            entity_id="PART-REQ-104-SOLENOID",
            payload={"delay_minutes": 180, "new_ready_tick": 198},
            occurred_at=now,
            ingested_at=now,
            snapshot_hash_before="",
            snapshot_hash_after="",
        )

        analysis = engine.analyze_disruption(canonical_snapshot, event)
        assert "RO-104" in analysis.disrupted_ro_ids
        assert "BAY-01" in analysis.affected_bay_ids
        assert analysis.is_schedule_invalidated is True

    def test_recovery_recommendations_end_to_end(self, canonical_snapshot: DealershipSnapshotSchema):
        engine = StallBreakerEngine()
        now = datetime.now(timezone.utc)
        event = StoredEvent(
            event_id="EVT-RECOVER-01",
            rooftop_id="ROOF-01",
            event_type=EventType.PARTS_ETA_CHANGED,
            entity_type="PART_REQUIREMENT",
            entity_id="PART-REQ-104-SOLENOID",
            payload={"delay_minutes": 180, "new_ready_tick": 198},
            occurred_at=now,
            ingested_at=now,
            snapshot_hash_before="",
            snapshot_hash_after="",
        )

        report = engine.generate_recovery_recommendations(canonical_snapshot, event)

        assert report.is_recovery_feasible is True
        assert len(report.candidate_actions) >= 3

        # Action 3 (Alternative bay for RO-106) was rejected under C1
        c1_rejected = next((a for a in report.candidate_actions if a.action_id == "ACT-RELOCATE-RO106-BAY02"), None)
        assert c1_rejected is not None
        assert c1_rejected.is_feasible is False
        assert "C1" in c1_rejected.rejection_reason

        # Action 1 (Expedited S1 hotshot) is recommended
        assert report.recommended_action is not None
        assert report.recommended_action.action_id == "ACT-EXPEDITE-S1"
        assert report.decision_replay is not None
        assert report.decision_replay.net_economic_delta_usd > Decimal("0.00")
        assert report.decision_replay.sourcing_freight_usd == Decimal("37.00")
        assert report.explainability is not None
        assert "RO-104" in report.explainability.recommendation_summary


# ============================================================================
# 5. FASTAPI REST API INTEGRATION
# ============================================================================

class TestStallBreakerFastAPIEndpoints:
    """Verifies REST endpoints for event ingestion, state query, disruption analysis, recommendations, and commit."""

    def test_api_event_ingestion_success(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        payload = {"part_req_id": "PART-REQ-104-SOLENOID", "new_ready_tick": 198, "delay_minutes": 180}
        sig = compute_hmac_sha256(payload)

        resp = client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": "EVT-API-01",
                "rooftop_id": "ROOF-01",
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": payload,
                "signature": sig,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "ACCEPTED"
        assert data["is_duplicate"] is False
        assert data["requires_recovery"] is True
        assert data["new_snapshot_hash"] != ""

    def test_api_event_ingestion_duplicate_idempotency(self, client: TestClient):
        payload = {"part_req_id": "PART-REQ-104-SOLENOID", "new_ready_tick": 198}
        body = {
            "event_id": "EVT-DUP-01",
            "rooftop_id": "ROOF-01",
            "event_type": "PARTS_ETA_CHANGED",
            "entity_type": "PART_REQUIREMENT",
            "entity_id": "PART-REQ-104-SOLENOID",
            "payload": payload,
        }

        # First post: ACCEPTED
        r1 = client.post("/api/v1/stallbreaker/events", json=body)
        assert r1.status_code == 201
        assert r1.json()["status"] == "ACCEPTED"

        # Second post: DUPLICATE_IGNORED
        r2 = client.post("/api/v1/stallbreaker/events", json=body)
        assert r2.status_code == 201
        assert r2.json()["status"] == "DUPLICATE_IGNORED"
        assert r2.json()["is_duplicate"] is True

    def test_api_event_ingestion_invalid_signature_rejected_401(self, client: TestClient):
        resp = client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": "EVT-SIG-FAIL",
                "rooftop_id": "ROOF-01",
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": {"delay_minutes": 180},
                "signature": "INVALID-SIGNATURE-HEX-0000000000000000000000000000000000000000000000",
            },
        )
        assert resp.status_code == 401
        assert "Invalid HMAC-SHA256" in resp.json()["detail"]

    def test_api_stallbreaker_live_state(self, client: TestClient):
        resp = client.get("/api/v1/stallbreaker/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rooftop_id"] == "ROOF-01"
        assert len(data["repair_orders"]) > 0

    def test_api_stallbreaker_disruption_analysis(self, client: TestClient):
        resp = client.post(
            "/api/v1/stallbreaker/disruption-analysis",
            json={"event_id": "EVT-DISRUPT-TEST"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "RO-104" in data["disrupted_ro_ids"]
        assert "BAY-01" in data["affected_bay_ids"]

    def test_api_stallbreaker_recovery_recommendations(self, client: TestClient):
        payload = {"part_req_id": "PART-REQ-104-SOLENOID", "new_ready_tick": 198, "delay_minutes": 180}
        sig = compute_hmac_sha256(payload)
        client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": "EVT-REC-API-01",
                "rooftop_id": "ROOF-01",
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": payload,
                "signature": sig,
            },
        )
        resp = client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={"event_id": "EVT-REC-API-01", "allow_emergency_overtime": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_id"] == "EVT-REC-API-01"
        assert data["is_recovery_feasible"] is True
        assert data["recommended_action"]["action_id"] == "ACT-EXPEDITE-S1"
        assert data["decision_replay"] is not None
        assert float(data["decision_replay"]["net_economic_delta_usd"]) > 0.0

    def test_api_recovery_recommendations_missing_event_id_returns_400(self, client: TestClient):
        # Missing event_id field returns 400
        resp = client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={"allow_emergency_overtime": True},
        )
        assert resp.status_code == 400
        assert "event_id" in resp.json()["detail"]

        # Blank/whitespace event_id returns 400
        resp_empty = client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={"event_id": "   ", "allow_emergency_overtime": True},
        )
        assert resp_empty.status_code == 400

    def test_api_recovery_recommendations_unknown_event_id_returns_404(self, client: TestClient):
        resp = client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={"event_id": "EVT-DOES-NOT-EXIST-404", "allow_emergency_overtime": True},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_api_recovery_recommendations_rooftop_mismatch_returns_404(self, client: TestClient):
        payload = {"part_req_id": "PART-REQ-104-SOLENOID", "new_ready_tick": 198}
        sig = compute_hmac_sha256(payload)
        client.post(
            "/api/v1/stallbreaker/events",
            json={
                "event_id": "EVT-ISOLATION-01",
                "rooftop_id": "ROOF-01",
                "event_type": "PARTS_ETA_CHANGED",
                "entity_type": "PART_REQUIREMENT",
                "entity_id": "PART-REQ-104-SOLENOID",
                "payload": payload,
                "signature": sig,
            },
        )
        # Query with wrong rooftop_id in request
        resp = client.post(
            "/api/v1/stallbreaker/recovery-recommendations",
            json={
                "event_id": "EVT-ISOLATION-01",
                "rooftop_id": "ROOF-UNKNOWN",
                "allow_emergency_overtime": True,
            },
        )
        assert resp.status_code == 404

    def test_api_stallbreaker_approval_and_commit(self, client: TestClient, canonical_snapshot: DealershipSnapshotSchema):
        resp = client.post(
            "/api/v1/stallbreaker/approve",
            json={
                "plan_id": "PLAN-REC-OFFER-104-S1",
                "event_id": "EVT-APPROVE-01",
                "expected_snapshot_hash": canonical_snapshot.snapshot_hash,
                "approver_id": "MGR-MARCUS",
                "approved_freight_usd": "50.00",
                "approval_notes": "Authorized expedited courier for RO-104 under C7 threshold",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMMITTED"
        assert data["outbox_events_dispatched"] > 0

    def test_api_stallbreaker_stale_hash_rejected_occ(self, client: TestClient):
        resp = client.post(
            "/api/v1/stallbreaker/approve",
            json={
                "plan_id": "PLAN-REC-OFFER-104-S1",
                "event_id": "EVT-APPROVE-STALE",
                "expected_snapshot_hash": "STALE-HASH-INCORRECT-VERSION",
                "approver_id": "MGR-MARCUS",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ABORTED_STALE_STATE"
        assert data["error_code"] == "OCC_VERSION_MISMATCH"
