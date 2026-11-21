"""StallBreaker: Event-Driven Disruption and Recovery Intelligence Subsystem."""

from app.stallbreaker.approval import StallBreakerApprovalGateway, stallbreaker_approval_gateway
from app.stallbreaker.engine import StallBreakerEngine, stallbreaker_engine
from app.stallbreaker.event_store import EventTamperError, StallBreakerEventStore, stallbreaker_event_store
from app.stallbreaker.models import (
    EventIngestRequest,
    EventIngestResponse,
    EventType,
    StallBreakerActionType,
    StallBreakerApprovalRequest,
    StallBreakerCandidateAction,
    StallBreakerDisruptionAnalysis,
    StallBreakerRecoveryReport,
    StoredEvent,
)
from app.stallbreaker.security import compute_hmac_sha256, verify_hmac_sha256
from app.stallbreaker.state_transitions import DealershipStateMutator

__all__ = [
    "EventType",
    "StallBreakerActionType",
    "EventIngestRequest",
    "EventIngestResponse",
    "StoredEvent",
    "StallBreakerDisruptionAnalysis",
    "StallBreakerCandidateAction",
    "StallBreakerRecoveryReport",
    "StallBreakerApprovalRequest",
    "compute_hmac_sha256",
    "verify_hmac_sha256",
    "EventTamperError",
    "StallBreakerEventStore",
    "stallbreaker_event_store",
    "DealershipStateMutator",
    "StallBreakerEngine",
    "stallbreaker_engine",
    "StallBreakerApprovalGateway",
    "stallbreaker_approval_gateway",
]
