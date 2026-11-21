"""Deterministic Fixture Loading and Pydantic v2 Ingestion Pipeline."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.snapshot import compute_snapshot_hash_from_dict
from app.fixtures import S_MATH_01_FIXTURE_PATH
from app.optimise.evidence import (
    CustomerAuthorizationEvidence,
    ManagerFreightApprovalEvidence,
    TaskExecutionProgressEvidence,
    TechnicianFairnessEvidence,
    VehiclePhysicalEvidence,
    WorkshopEvidenceBundle,
)
from app.schemas.domain import DealershipSnapshotSchema


def load_fixture_raw(path: Optional[Path] = None) -> Dict[str, Any]:
    """Reads raw JSON fixture from file path."""
    fixture_path = path or S_MATH_01_FIXTURE_PATH
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found at: {fixture_path}")
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_fixture_data(path: Optional[Path] = None) -> DealershipSnapshotSchema:
    """Loads, validates, and computes the deterministic snapshot hash for a fixture.
    
    Returns:
        Validated DealershipSnapshotSchema instance with snapshot_hash populated.
    """
    raw_data = load_fixture_raw(path)
    
    # Compute deterministic SHA-256 snapshot hash over raw payload
    computed_hash = compute_snapshot_hash_from_dict(raw_data)
    raw_data["snapshot_hash"] = computed_hash
    
    # Full Pydantic v2 validation including referential integrity checks
    validated_snapshot = DealershipSnapshotSchema.model_validate(raw_data)
    return validated_snapshot


def load_canonical_evidence(
    snapshot: DealershipSnapshotSchema,
    current_tick: int = 159,
) -> WorkshopEvidenceBundle:
    """Constructs the canonical WorkshopEvidenceBundle for S-MATH-01 snapshot."""
    customer_auths = {}
    for r in snapshot.repair_orders:
        customer_auths[r.ro_id] = CustomerAuthorizationEvidence(
            ro_id=r.ro_id,
            is_authorized=True,
            authorized_amount_usd=Decimal("500.00"),
        )

    freight_approvals = {}
    for o in snapshot.supplier_offers:
        freight_approvals[o.offer_id] = ManagerFreightApprovalEvidence(
            offer_id=o.offer_id,
            is_approved=True,
            approved_amount_usd=o.freight_surcharge_usd,
            approved_by="MGR-MARCUS",
        )

    progress_evidence = {}
    for t in snapshot.tasks:
        status_val = t.status.value if hasattr(t.status, "value") else str(t.status)
        rem = t.estimated_duration_ticks if status_val != "COMPLETED" else 0
        ro = next((r for r in snapshot.repair_orders if r.ro_id == t.ro_id), None)
        progress_evidence[t.task_id] = TaskExecutionProgressEvidence(
            task_id=t.task_id,
            status=t.status,
            current_tick=current_tick,
            existing_bay_id=ro.assigned_bay_id if (ro and status_val in ("IN_PROGRESS", "STALLED")) else None,
            remaining_duration_ticks=rem,
            is_assignment_locked=True,
        )

    vehicle_evidence = {}
    for r in snapshot.repair_orders:
        state_val = r.physical_state.value if hasattr(r.physical_state, "value") else str(r.physical_state)
        is_imm = state_val == "IMMOBILIZED_ON_LIFT"
        is_holding = state_val == "IN_HOLDING"
        v_ev = VehiclePhysicalEvidence(
            vehicle_id=r.vehicle_id,
            ro_id=r.ro_id,
            physical_state=r.physical_state,
            current_bay_id=r.assigned_bay_id if is_imm else None,
            is_in_holding=is_holding,
            vehicle_weight_lbs=getattr(r, "vehicle_weight_lbs", 3800) or 3800,
            fitment_verified=True,
            occupancy_start_tick=current_tick if is_imm else None,
        )
        vehicle_evidence[r.vehicle_id] = v_ev
        vehicle_evidence[r.ro_id] = v_ev

    fairness_evidence = {}
    for tech in snapshot.technicians:
        fairness_evidence[tech.tech_id] = TechnicianFairnessEvidence(
            tech_id=tech.tech_id,
            skill_group="GENERAL_MECHANICAL",
            historical_allocated_hours=Decimal("40.0"),
            median_peer_hours=Decimal("40.0"),
        )

    return WorkshopEvidenceBundle(
        current_tick=current_tick,
        available_porter_tech_ids={t.tech_id for t in snapshot.technicians} | {"PORTER-01"},
        customer_authorizations=customer_auths,
        manager_freight_approvals=freight_approvals,
        task_progress=progress_evidence,
        vehicle_evidence=vehicle_evidence,
        technician_fairness=fairness_evidence,
    )
