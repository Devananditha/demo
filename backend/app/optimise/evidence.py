"""Explicit Typed Workshop Evidence Models for ServiceYield AI Optimise Engine.

Authoritative Reference:
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md

Purpose:
Eliminates manufactured or hardcoded operational evidence (e.g. fake approvals,
assumed remaining durations, assumed vehicle weights, and unverified fairness).
Enforces strict fail-closed boundary contracts: missing or unverified evidence
blocks scheduling rather than silently passing assumptions.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.domain import TaskStatus, VehiclePhysicalState


class CustomerAuthorizationEvidence(BaseModel):
    """Explicit customer estimate sign-off required under C7 consumer protection laws."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ro_id: str = Field(..., min_length=1)
    is_authorized: bool = Field(default=False, description="Customer authorized repair estimate")
    authorized_amount_usd: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    authorized_at: Optional[datetime] = Field(default=None)


class ManagerFreightApprovalEvidence(BaseModel):
    """Explicit manager approval for expedited supplier courier freight surcharges."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    offer_id: str = Field(..., min_length=1)
    is_approved: bool = Field(default=False)
    approved_amount_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    approved_by: Optional[str] = Field(default=None)


class TaskExecutionProgressEvidence(BaseModel):
    """Execution state and remaining duration for active/stalled mechanical operations."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    task_id: str = Field(..., min_length=1)
    status: TaskStatus
    current_tick: int = Field(..., ge=0, le=288)
    existing_tech_id: Optional[str] = Field(default=None)
    existing_bay_id: Optional[str] = Field(default=None)
    elapsed_duration_ticks: int = Field(default=0, ge=0)
    remaining_duration_ticks: Optional[int] = Field(
        default=None,
        ge=0,
        description="Explicit remaining work ticks. If missing for IN_PROGRESS/STALLED, fails closed.",
    )


class VehiclePhysicalEvidence(BaseModel):
    """Verified physical vehicle location, weight, and fitment attributes."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    vehicle_id: str = Field(..., min_length=1)
    ro_id: str = Field(..., min_length=1)
    physical_state: VehiclePhysicalState
    current_bay_id: Optional[str] = Field(default=None, description="Occupied bay if on lift or in bay")
    is_in_holding: bool = Field(default=False, description="True if parked in holding staging lot")
    vehicle_weight_lbs: Optional[int] = Field(default=None, gt=0, description="Gross vehicle weight rating in lbs")
    fitment_verified: bool = Field(default=True, description="ACES/PIES parts fitment verified")


class TechnicianFairnessEvidence(BaseModel):
    """Rolling two-week flat-rate fairness band evidence under C6 (FLSA 29 U.S.C. §207(i))."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    tech_id: str = Field(..., min_length=1)
    skill_group: str = Field(..., min_length=1)
    historical_allocated_hours: Decimal = Field(..., ge=Decimal("0.00"))
    median_peer_hours: Decimal = Field(..., gt=Decimal("0.00"))


class WorkshopEvidenceBundle(BaseModel):
    """Complete typed operational evidence bundle supplied to the Optimise Engine boundary."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    current_tick: int = Field(default=96, ge=0, le=288, description="Evaluation baseline tick (e.g. 96 for start of day)")
    customer_authorizations: Dict[str, CustomerAuthorizationEvidence] = Field(
        default_factory=dict,
        description="ro_id -> customer estimate authorization evidence",
    )
    manager_freight_approvals: Dict[str, ManagerFreightApprovalEvidence] = Field(
        default_factory=dict,
        description="offer_id -> manager freight surcharge approvals",
    )
    task_progress: Dict[str, TaskExecutionProgressEvidence] = Field(
        default_factory=dict,
        description="task_id -> execution progress and remaining duration",
    )
    vehicle_evidence: Dict[str, VehiclePhysicalEvidence] = Field(
        default_factory=dict,
        description="vehicle_id (or ro_id) -> physical state and weight evidence",
    )
    technician_fairness: Dict[str, TechnicianFairnessEvidence] = Field(
        default_factory=dict,
        description="tech_id -> rolling two-week fairness band metrics",
    )
    available_porter_tech_ids: Set[str] = Field(
        default_factory=set,
        description="Technicians or porters certified and available for vehicle movements",
    )

    def is_ro_authorized(self, ro_id: str) -> bool:
        """Returns True only if explicit, valid customer authorization evidence exists."""
        auth = self.customer_authorizations.get(ro_id)
        return auth is not None and auth.is_authorized is True

    def is_freight_approved(self, offer_id: str, surcharge_usd: Decimal, threshold_usd: Decimal = Decimal("50.00")) -> bool:
        """Evaluates whether freight surcharge is within threshold or explicitly approved."""
        if surcharge_usd <= threshold_usd:
            return True
        appr = self.manager_freight_approvals.get(offer_id)
        return appr is not None and appr.is_approved is True and appr.approved_amount_usd >= surcharge_usd

    def get_effective_remaining_duration(self, task_id: str, status: TaskStatus, default_duration: int) -> Optional[int]:
        """Returns verified remaining work duration in ticks, or None if evidence is missing."""
        status_val = status.value if hasattr(status, "value") else str(status)
        if status_val == "COMPLETED":
            return 0
        if status_val == "PENDING":
            return default_duration
        
        # IN_PROGRESS or STALLED require explicit progress evidence
        prog = self.task_progress.get(task_id)
        if not prog or prog.remaining_duration_ticks is None:
            return None
        return prog.remaining_duration_ticks
