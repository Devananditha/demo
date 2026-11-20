"""Targeted Tests for Read-Only Predict Readiness API."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import REFERENCE_CURRENT_TICK, app
from app.data.loader import load_fixture_data
from app.predict.models import ReadinessState


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def canonical_snapshot():
    """Loads the canonical fixture data."""
    return load_fixture_data()


def test_api_health_endpoint(client):
    """1. Health endpoint returns 200 OK and expected status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_state_endpoint(client, canonical_snapshot):
    """2. State endpoint returns canonical rooftop state and snapshot hash."""
    response = client.get("/api/v1/state")
    assert response.status_code == 200
    data = response.json()

    assert data["rooftop_id"] == canonical_snapshot.rooftop.rooftop_id
    assert data["snapshot_hash"] == canonical_snapshot.snapshot_hash
    assert data["evaluation_tick"] == REFERENCE_CURRENT_TICK
    assert data["operating_day_end_tick"] == canonical_snapshot.rooftop.operating_day_end_tick
    assert data["overtime_cutoff_tick"] == canonical_snapshot.rooftop.overtime_cutoff_tick

    # Verify repair orders match canonical fixture without missing data invention
    ros = {ro["ro_id"]: ro for ro in data["repair_orders"]}
    assert len(ros) == 6
    assert ros["RO-101"]["assigned_bay_id"] == "BAY-02"
    assert ros["RO-102"]["assigned_bay_id"] == "BAY-03"
    assert ros["RO-103"]["assigned_bay_id"] is None
    assert ros["RO-104"]["assigned_bay_id"] == "BAY-01"
    assert ros["RO-104"]["physical_state"] == "IMMOBILIZED_ON_LIFT"
    assert ros["RO-105"]["assigned_bay_id"] is None
    assert ros["RO-105"]["physical_state"] == "IN_HOLDING"
    assert ros["RO-106"]["assigned_bay_id"] is None
    assert ros["RO-106"]["physical_state"] == "IN_HOLDING"


def test_api_predict_readiness_success(client, canonical_snapshot):
    """3. Readiness endpoint returns six actual classifier assessments and summary counts."""
    payload = {
        "rooftop_id": canonical_snapshot.rooftop.rooftop_id,
        "snapshot_hash": canonical_snapshot.snapshot_hash,
    }
    response = client.post("/api/v1/predict/readiness", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["rooftop_id"] == canonical_snapshot.rooftop.rooftop_id
    assert data["snapshot_hash"] == canonical_snapshot.snapshot_hash

    assessments = {a["ro_id"]: a for a in data["assessments"]}
    assert len(assessments) == 6

    # Verify expected reference classifications from actual classifier
    assert assessments["RO-101"]["state"] == ReadinessState.READY.value
    assert assessments["RO-102"]["state"] == ReadinessState.READY.value
    assert assessments["RO-103"]["state"] == ReadinessState.READY.value
    assert assessments["RO-104"]["state"] == ReadinessState.AT_RISK.value
    assert assessments["RO-105"]["state"] == ReadinessState.BLOCKED.value
    assert assessments["RO-106"]["state"] == ReadinessState.READY.value

    # Verify summary counts
    assert data["summary_counts"]["READY"] == 4
    assert data["summary_counts"]["AT_RISK"] == 1
    assert data["summary_counts"]["BLOCKED"] == 1
    assert data["summary_counts"].get("UNKNOWN", 0) == 0

    # Verify contract uses 'calibration' serialization alias and does not expose 'calibration_status'
    for ro_id, assessment in assessments.items():
        assert "calibration" in assessment, f"Expected 'calibration' in {ro_id} assessment"
        assert "calibration_status" not in assessment, f"Did not expect 'calibration_status' in {ro_id} assessment"

    # Verify RO-104 details are preserved
    ro_104 = assessments["RO-104"]
    assert ro_104["has_recovery_alternative"] is True
    assert ro_104["best_alternative_usable_tick"] == 165
    assert ro_104["slack"]["latest_feasible_start_tick"] == 168
    assert ro_104["slack"]["usable_ready_tick"] == 198
    assert "NEGATIVE_SLACK_RECOVERABLE_VIA_ALTERNATIVE" in ro_104["reasons"]


def test_api_predict_readiness_stale_hash_rejected(client, canonical_snapshot):
    """4. Rejection of a stale snapshot hash with HTTP 409 Conflict."""
    payload = {
        "rooftop_id": canonical_snapshot.rooftop.rooftop_id,
        "snapshot_hash": "deadbeef" * 8,
    }
    response = client.post("/api/v1/predict/readiness", json=payload)
    assert response.status_code == 409
    assert "Stale snapshot hash" in response.json()["detail"]


def test_api_predict_readiness_unknown_rooftop_rejected(client, canonical_snapshot):
    """5. Rejection of an unknown rooftop with HTTP 404 Not Found."""
    payload = {
        "rooftop_id": "ROOF-UNKNOWN-99",
        "snapshot_hash": canonical_snapshot.snapshot_hash,
    }
    response = client.post("/api/v1/predict/readiness", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
