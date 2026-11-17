"""Verification Data Models and Schemas for L4 Independent Verifier.

Authoritative Reference:
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.constraints.rules import ConstraintViolation


class ScheduledAssignment(BaseModel):
    """Discrete task execution assignment within a candidate schedule."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    task_id: str = Field(..., min_length=1, description="Unique task identifier")
    ro_id: str = Field(..., min_length=1, description="Associated repair order ID")
    tech_id: str = Field(..., min_length=1, description="Assigned technician ID")
    bay_id: str = Field(..., min_length=1, description="Assigned bay ID")
    start_tick: int = Field(..., ge=0, le=288, description="Execution start tick [0, 288]")
    end_tick: int = Field(..., ge=0, le=288, description="Execution finish tick [0, 288]")

    @model_validator(mode="after")
    def validate_duration(self) -> "ScheduledAssignment":
        if self.start_tick >= self.end_tick:
            raise ValueError(f"Task {self.task_id} start_tick ({self.start_tick}) must be strictly less than end_tick ({self.end_tick})")
        return self


class VehicleBayOccupancy(BaseModel):
    """Physical vehicle occupancy window in a bay (including idle/stalled intervals)."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    vehicle_id: str = Field(..., min_length=1)
    ro_id: str = Field(..., min_length=1)
    bay_id: str = Field(..., min_length=1)
    start_tick: int = Field(..., ge=0, le=288)
    end_tick: int = Field(..., ge=0, le=288)

    @model_validator(mode="after")
    def validate_window(self) -> "VehicleBayOccupancy":
        if self.start_tick >= self.end_tick:
            raise ValueError(f"Occupancy start_tick ({self.start_tick}) must be strictly less than end_tick ({self.end_tick})")
        return self


class CandidateSchedulePlan(BaseModel):
    """Complete candidate workshop schedule submitted to L4 Verifier for certification."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    plan_id: str = Field(default="PLAN-CANDIDATE-01")
    rooftop_id: str = Field(..., min_length=1)
    snapshot_hash: str = Field(..., min_length=1, description="State snapshot SHA-256 for OCC audit")
    assignments: List[ScheduledAssignment] = Field(default_factory=list)
    vehicle_occupancies: List[VehicleBayOccupancy] = Field(default_factory=list)
    customer_authorizations: Dict[str, bool] = Field(
        default_factory=dict, description="ro_id -> authorization status (defaults to True if omitted)"
    )
    manager_freight_approvals: Dict[str, bool] = Field(
        default_factory=dict, description="offer_id -> approval status"
    )
    allow_emergency_overtime: bool = Field(
        default=False, description="Whether authorized emergency overtime beyond shift end is permitted"
    )


@dataclass
class VerificationResult:
    """Independent audit certification report emitted by L4 Sweep Oracle."""
    plan_id: str
    snapshot_hash: str
    is_valid: bool
    violations: List[ConstraintViolation] = field(default_factory=list)
    execution_time_ms: float = 0.0

    @property
    def status(self) -> str:
        return "PASS" if self.is_valid else "FAIL"

    @property
    def total_violations(self) -> int:
        return len(self.violations)

    def summary(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "is_valid": self.is_valid,
            "total_violations": self.total_violations,
            "execution_time_ms": round(self.execution_time_ms, 3),
            "violations": [v.to_dict() for v in self.violations],
        }
