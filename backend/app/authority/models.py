"""Domain Models and Result Schemas for Authority & Commit Gateway.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md (Section 2.4)
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4.2 & 6)
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.6)
- docs/12_VERIFICATION_AND_REVALIDATION.md
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommitStatus(str, Enum):
    """Execution status returned by the Authority Commit Gateway."""
    COMMITTED = "COMMITTED"
    ABORTED_STALE_STATE = "ABORTED_STALE_STATE"
    REJECTED_UNAUTHORIZED = "REJECTED_UNAUTHORIZED"
    REJECTED_UNCERTIFIED = "REJECTED_UNCERTIFIED"
    REJECTED_EXPIRED = "REJECTED_EXPIRED"
    INVALID_REQUEST = "INVALID_REQUEST"


class OutboxEventType(str, Enum):
    """Categorical types of transactional integration events dispatched on commit."""
    DISPATCH_PLAN_COMMITTED = "DISPATCH_PLAN_COMMITTED"
    SUPPLIER_ORDER_EXPEDITED = "SUPPLIER_ORDER_EXPEDITED"
    CUSTOMER_PROMISE_UPDATED = "CUSTOMER_PROMISE_UPDATED"
    VEHICLE_MOVEMENT_DISPATCHED = "VEHICLE_MOVEMENT_DISPATCHED"


class OutboxEvent(BaseModel):
    """Transactional outbox event record ready for external asynchronous publishing."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event_id: str
    aggregate_type: str = Field(..., description="e.g. ROOFTOP, SCHEDULE_PLAN, SUPPLIER_ORDER")
    aggregate_id: str = Field(..., description="Identifier of the target aggregate")
    event_type: OutboxEventType
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="PENDING", description="PENDING, DISPATCHED, or FAILED")


class ManagerRecoveryApproval(BaseModel):
    """Explicit human service manager authorization for a recovery plan."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    approval_id: str = Field(default_factory=lambda: f"APPRV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    plan_id: str = Field(..., min_length=1)
    snapshot_hash: str = Field(..., min_length=1)
    approver_id: str = Field(..., min_length=1)
    approved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_freight_usd: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    approval_notes: Optional[str] = None
    valid_until: Optional[datetime] = None


class CommitRequest(BaseModel):
    """Service Manager submission request to finalize and commit a recovery plan."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    plan_id: str = Field(..., min_length=1)
    expected_snapshot_hash: str = Field(..., min_length=1)
    approver_id: str = Field(..., min_length=1)
    approval_notes: Optional[str] = None
    approved_freight_usd: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    timestamp_utc: Optional[datetime] = None


class CommitResult(BaseModel):
    """Deterministic, idempotent response returned by the Authority Commit Gateway."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: CommitStatus
    plan_id: str
    committed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    error_message: Optional[str] = None
    expected_hash: Optional[str] = None
    current_hash: Optional[str] = None
    outbox_events_dispatched: int = 0
    outbox_events: List[OutboxEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_error_message(self) -> "CommitResult":
        if self.message and not self.error_message:
            self.error_message = self.message
        elif self.error_message and not self.message:
            self.message = self.error_message
        return self
