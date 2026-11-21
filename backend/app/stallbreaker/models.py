"""Domain Models and Data Schemas for StallBreaker Event-Driven Disruption Engine.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md
- docs/03_PRODUCT_REQUIREMENTS.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.recover.models import RecoveryAlternative
from app.replay.models import DecisionExplainability, DecisionReplayDiff
from app.schemas.domain import EconomicParametersSchema


class EventType(str, Enum):
    """Categorical taxonomy of event-driven shop telemetry triggers."""
    RO_LINE_READY = "RO_LINE_READY"
    RO_OPENED = "RO_OPENED"
    PARTS_ETA_CHANGED = "PARTS_ETA_CHANGED"
    PART_UNAVAILABLE = "PART_UNAVAILABLE"
    BAY_RESERVATION_CHANGED = "BAY_RESERVATION_CHANGED"
    TECHNICIAN_UNAVAILABLE = "TECHNICIAN_UNAVAILABLE"
    OPERATION_COMPLETED = "OPERATION_COMPLETED"


class StallBreakerActionType(str, Enum):
    """Taxonomy of candidate operational recovery actions."""
    RESCHEDULE_OPERATION = "RESCHEDULE_OPERATION"
    ASSIGN_ALTERNATIVE_BAY = "ASSIGN_ALTERNATIVE_BAY"
    REASSIGN_QUALIFIED_TECHNICIAN = "REASSIGN_QUALIFIED_TECHNICIAN"
    DELAY_UNTIL_PARTS_READY = "DELAY_UNTIL_PARTS_READY"
    EXPEDITED_SOURCING_ALTERNATIVE = "EXPEDITED_SOURCING_ALTERNATIVE"


class EventIngestRequest(BaseModel):
    """Incoming external event payload with optional HMAC signature and OCC hash."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event_id: str = Field(..., min_length=1, description="Globally unique external event identifier")
    rooftop_id: str = Field(default="ROOF-01", min_length=1, description="Target dealership rooftop identifier")
    event_type: EventType = Field(..., description="Validated domain event type")
    entity_type: str = Field(..., min_length=1, description="Entity type: PART_REQUIREMENT, REPAIR_ORDER, BAY, TECHNICIAN, TASK")
    entity_id: str = Field(..., min_length=1, description="Identifier of the directly affected domain entity")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific metadata and parameters")
    occurred_at: Optional[datetime] = Field(default=None, description="Event generation timestamp")
    signature: Optional[str] = Field(default=None, description="HMAC-SHA256 hex digest for webhook security")
    expected_snapshot_hash: Optional[str] = Field(default=None, description="Optional OCC version check")


class EventIngestResponse(BaseModel):
    """Result of external event ingestion."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: str = Field(..., description="ACCEPTED, DUPLICATE_IGNORED, or REJECTED")
    event_id: str
    is_duplicate: bool = Field(default=False)
    previous_snapshot_hash: str
    new_snapshot_hash: str
    requires_recovery: bool = Field(default=False)
    disruption_summary: Optional[str] = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StoredEvent(BaseModel):
    """Persisted event log entry in the StallBreaker audit ledger."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event_id: str
    rooftop_id: str
    event_type: EventType
    entity_type: str
    entity_id: str
    payload: Dict[str, Any]
    occurred_at: datetime
    ingested_at: datetime
    signature: Optional[str] = None
    snapshot_hash_before: str
    snapshot_hash_after: str


class StallBreakerDisruptionAnalysis(BaseModel):
    """Calculated consequences of an event on shop capacity and active schedules."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event_id: str
    event_type: EventType
    disrupted_ro_ids: List[str] = Field(default_factory=list)
    affected_bay_ids: List[str] = Field(default_factory=list)
    affected_tech_ids: List[str] = Field(default_factory=list)
    invalidated_task_ids: List[str] = Field(default_factory=list)
    is_schedule_invalidated: bool = False
    constraint_violations_detected: List[str] = Field(default_factory=list)
    impact_summary: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StallBreakerCandidateAction(BaseModel):
    """Individual candidate recovery action evaluated by StallBreaker."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    action_id: str
    action_type: StallBreakerActionType
    target_ro_id: str
    target_task_id: Optional[str] = None
    source_bay_id: Optional[str] = None
    target_bay_id: Optional[str] = None
    source_tech_id: Optional[str] = None
    target_tech_id: Optional[str] = None
    sourcing_offer_id: Optional[str] = None
    freight_surcharge_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    is_feasible: bool = True
    rejection_reason: Optional[str] = None
    description: str


class StallBreakerRecoveryReport(BaseModel):
    """Full disruption-to-recovery intelligence output for Service Managers."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event_id: str
    event_type: EventType
    disruption_analysis: StallBreakerDisruptionAnalysis
    candidate_actions: List[StallBreakerCandidateAction] = Field(default_factory=list)
    evaluated_alternatives: List[RecoveryAlternative] = Field(default_factory=list)
    recommended_action: Optional[StallBreakerCandidateAction] = None
    recommended_plan_id: Optional[str] = None
    baseline_plan_id: str
    is_recovery_feasible: bool = True
    infeasibility_reason: Optional[str] = None
    decision_replay: Optional[DecisionReplayDiff] = None
    explainability: Optional[DecisionExplainability] = None
    solve_time_ms: float = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StallBreakerApprovalRequest(BaseModel):
    """Version-bound manager approval request for a StallBreaker recovery action."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    plan_id: str = Field(..., min_length=1)
    event_id: str = Field(..., min_length=1)
    expected_snapshot_hash: str = Field(..., min_length=1)
    approver_id: str = Field(..., min_length=1)
    approved_freight_usd: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    approval_notes: Optional[str] = None
