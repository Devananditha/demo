"""Domain Models and Data Schemas for ServiceYield AI Recover Engine.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md (Section 2.3)
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.4)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field

from app.optimise.models import BayHourShadowPrice, ScheduleResult
from app.replay.models import DecisionExplainability, DecisionReplayDiff
from app.verifier.models import CandidateSchedulePlan, VerificationResult


class DisruptionType(str, Enum):
    """Categorical taxonomy of shop-floor disruption triggers."""
    PARTS_DELAY = "PARTS_DELAY"
    SUPPLIER_ETA_SLIP = "SUPPLIER_ETA_SLIP"
    SUPPLIER_CANCELLATION = "SUPPLIER_CANCELLATION"
    PART_BACKORDERED = "PART_BACKORDERED"
    PART_DEFECTIVE = "PART_DEFECTIVE"
    TECHNICIAN_ABSENCE = "TECHNICIAN_ABSENCE"
    BAY_EQUIPMENT_FAILURE = "BAY_EQUIPMENT_FAILURE"
    DURATION_OVERRUN = "DURATION_OVERRUN"


class DisruptionEvent(BaseModel):
    """Normalized disruption trigger event ingested by the Recover Engine."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event_id: str = Field(default_factory=lambda: f"DISRUPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    disrupted_ro_id: str = Field(..., min_length=1)
    disrupted_part_req_id: Optional[str] = Field(default=None)
    trigger_tick: int = Field(..., ge=0, le=288)
    trigger_time: Optional[str] = Field(default=None)
    event_type: DisruptionType = Field(default=DisruptionType.SUPPLIER_ETA_SLIP)
    disruption_type: Optional[DisruptionType] = None
    original_ready_tick: Optional[int] = None
    delayed_ready_tick: Optional[int] = None
    description: Optional[str] = None
    event_timestamp_utc: Optional[datetime] = None
    primary_supplier_delay_minutes: int = Field(default=0, ge=0)
    affected_bay_id: Optional[str] = Field(default=None)
    affected_tech_id: Optional[str] = Field(default=None)
    reasons: List[str] = Field(default_factory=list)
    reported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DependencyBlastRadius(BaseModel):
    """Direct and downstream dependencies affected by a disruption event."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    disrupted_ro_id: str
    affected_task_ids: List[str] = Field(default_factory=list)
    immobilized_bay_id: Optional[str] = None
    is_immobilized_on_lift: bool = False
    competing_ro_ids: List[str] = Field(default_factory=list, description="ROs queued or competing for same bay or skill")
    competing_task_ids: List[str] = Field(default_factory=list)
    critical_path_ticks: int = Field(default=0, ge=0)


class SourcingCandidate(BaseModel):
    """Candidate sourcing option evaluated by branch-and-bound search."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    option_id: str = Field(..., min_length=1)
    offer_id: str = Field(..., min_length=1)
    part_req_id: str = Field(..., min_length=1)
    supplier_id: str = Field(..., min_length=1)
    supplier_name: str = Field(..., min_length=1)
    unit_cost_usd: Decimal = Field(..., ge=Decimal("0.00"))
    freight_surcharge_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    total_sourcing_cost_usd: Decimal = Field(..., ge=Decimal("0.00"))
    quoted_eta_tick: int = Field(..., ge=0, le=288)
    receiving_inspection_minutes: int = Field(default=0, ge=0)
    usable_ready_tick: int = Field(..., ge=0, le=288)
    is_feasible: bool = Field(default=True)
    rejection_reason: Optional[str] = None

    # Branch-and-bound lower bounds
    critical_path_lower_bound_usd: Decimal = Field(default=Decimal("0.00"))
    parallel_bay_lower_bound_usd: Decimal = Field(default=Decimal("0.00"))
    combined_lower_bound_usd: Decimal = Field(default=Decimal("0.00"))
    is_pruned: bool = Field(default=False)
    pruning_reason: Optional[str] = None


class SourcingSearchResult(BaseModel):
    """Complete output of the branch-and-bound sourcing search."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    disrupted_part_req_id: str
    evaluated_offers_count: int = Field(..., ge=0)
    feasible_candidates: List[SourcingCandidate] = Field(default_factory=list)
    pruned_candidates: List[SourcingCandidate] = Field(default_factory=list)
    rejected_candidates: List[SourcingCandidate] = Field(default_factory=list)
    best_candidate_id: Optional[str] = None
    search_duration_ms: float = Field(default=0.0, ge=0.0)


class RecoveryAlternative(BaseModel):
    """A fully rescheduled, verified, and economically evaluated recovery plan."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    option_id: str = Field(..., min_length=1)
    plan_id: str = Field(..., min_length=1)
    sourcing_candidate: SourcingCandidate
    schedule_result: Optional[ScheduleResult] = None
    
    # Financial and performance metrics
    gross_contribution_usd: Decimal
    sourcing_cost_usd: Decimal
    lateness_penalty_usd: Decimal
    net_objective_usd: Decimal
    net_recovery_delta_usd: Decimal = Field(description="Z_candidate - Z_baseline")
    
    # Operational metrics
    weighted_lateness_ticks: int
    bay_blocked_hours: Decimal
    bay_hour_shadow_price: Optional[BayHourShadowPrice] = None
    schedule_churn_count: int = 0
    
    # Verification & Certification
    is_verified: bool = Field(default=False, description="L4 Sweep-Line geometric verification")
    is_fully_certified: bool = Field(default=False, description="L4 + Supplemental dual certification")
    certification_status: str = Field(default="UNKNOWN")
    
    # Pareto status
    is_pareto_optimal: bool = Field(default=True)
    is_recommended: bool = Field(default=False)
    rationale: Optional[str] = None


class RecoveryRecommendationReport(BaseModel):
    """Executive decision report presented to the Service Manager."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    disruption_event: DisruptionEvent
    blast_radius: DependencyBlastRadius
    baseline_plan_id: str
    baseline_net_objective_usd: Decimal
    baseline_weighted_lateness_ticks: int
    
    recommended_option_id: Optional[str] = None
    recommended_plan_id: Optional[str] = None
    recommendation_rationale: str
    
    alternatives: List[RecoveryAlternative] = Field(default_factory=list)
    pareto_frontier: List[RecoveryAlternative] = Field(default_factory=list)
    
    decision_replay: Optional[DecisionReplayDiff] = Field(default=None, description="Detailed comparative Decision Replay deltas")
    explainability: Optional[DecisionExplainability] = Field(default=None, description="Detailed explainability breakdown")

    unresolved_risks: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    replan_duration_ms: float = Field(default=0.0, ge=0.0)
