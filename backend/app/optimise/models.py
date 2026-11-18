"""Data Models and Result Schemas for ServiceYield AI Optimise Engine.

Authoritative Reference:
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.3)
- docs/12_VERIFICATION_AND_REVALIDATION.md
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.verifier.models import CandidateSchedulePlan, VerificationResult


class SchedulerTier(str, Enum):
    """Hierarchy tier of the scheduling engine."""
    T1_HEURISTIC = "T1_HEURISTIC"
    T2_CPSAT = "T2_CPSAT"


class SolverStatus(str, Enum):
    """Rigorous solver outcome classification."""
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


class ShadowPriceStatus(str, Enum):
    """Mathematical exactness certification for marginal capacity calculation."""
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    UNAVAILABLE = "UNAVAILABLE"


class ObjectiveMetrics(BaseModel):
    """Individual observable components of the economic objective function."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    gross_contribution_usd: Decimal = Field(default=Decimal("0.00"), description="Gross labor contribution sum(M_i - C_i)")
    sourcing_cost_usd: Decimal = Field(default=Decimal("0.00"), description="Expedited parts/courier freight expense")
    weighted_lateness_ticks: int = Field(default=0, ge=0, description="Sum of w_r * max(0, C_r - D_r) in ticks")
    lateness_penalty_usd: Decimal = Field(default=Decimal("0.00"), description="lambda_late * weighted_lateness in USD")
    bay_blocked_ticks: int = Field(default=0, ge=0, description="Avoidable bay-blocking idle ticks")
    bay_blocked_penalty_usd: Decimal = Field(default=Decimal("0.00"), description="lambda_block * bay_blocked_ticks in USD")
    schedule_churn_score: Optional[int] = Field(default=None, ge=0, description="Number of task/resource reassignments from prior plan")
    schedule_churn_penalty_usd: Optional[Decimal] = Field(default=None, description="lambda_churn * churn_score in USD")
    churn_status: str = Field(default="NOT_APPLICABLE", description="AVAILABLE or NOT_APPLICABLE (when no prior plan exists)")
    net_objective_usd: Decimal = Field(default=Decimal("0.00"), description="Total net economic yield Z in USD")
    objective_completeness: str = Field(default="PARTIAL_CONFIGURED", description="PARTIAL_CONFIGURED or FULL_OBJECTIVE")
    configured_terms: List[str] = Field(default_factory=lambda: ["gross_contribution", "lateness_penalty"])
    unconfigured_terms: List[str] = Field(default_factory=lambda: ["sourcing_cost", "bay_blocked_penalty", "schedule_churn_penalty"])


class ScheduleResult(BaseModel):
    """Complete certified dispatch result from the Optimise Engine."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    plan_id: str = Field(..., min_length=1)
    rooftop_id: str = Field(..., min_length=1)
    snapshot_hash: str = Field(..., min_length=1)
    solver_tier: SchedulerTier
    solver_status: SolverStatus
    runtime_ms: float = Field(..., ge=0.0)
    objective_value_usd: Optional[Decimal] = None
    best_bound_usd: Optional[Decimal] = None
    optimality_gap: Optional[float] = None
    plan: CandidateSchedulePlan
    metrics: ObjectiveMetrics
    unscheduled_tasks: Dict[str, str] = Field(default_factory=dict, description="task_id -> explicit failure reason")
    verification_result: Optional[VerificationResult] = None
    is_verified: bool = Field(default=False, description="Certified PASS by independent L4 sweep-line oracle")
    supplemental_audit_result: Optional[Dict[str, Any]] = Field(default=None, description="Certified PASS by supplemental audit oracle")
    is_fully_certified: bool = Field(default=False, description="Certified PASS by both L4 Sweep Oracle and Supplemental Audit")
    evidence_coverage_gaps: List[str] = Field(default_factory=list)
    degradation_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BayHourShadowPrice(BaseModel):
    """Marginal capacity economic valuation nu_b(t) for a specific bay and time interval."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    rooftop_id: str = Field(..., min_length=1)
    bay_id: str = Field(..., min_length=1)
    interval_start_tick: int = Field(..., ge=0, le=288)
    interval_end_tick: int = Field(..., ge=0, le=288)
    duration_hours: Decimal = Field(..., gt=Decimal("0.00"), description="Interval duration Delta t in decimal hours")
    shadow_price_usd_per_hour: Decimal = Field(..., description="Canonical storage unit: Delta Z / Delta t in USD/bay-hour")
    shadow_price_usd_per_tick: Decimal = Field(..., description="Internal solver unit: shadow_price_hour / 12 in USD/bay-tick")
    baseline_objective_usd: Decimal = Field(..., description="Z*(C union {(b, t)})")
    perturbed_objective_usd: Decimal = Field(..., description="Z*(C setminus {(b, t)})")
    delta_objective_usd: Decimal = Field(..., description="Delta Z = Z*_avail - Z*_unavail")
    signed_delta_objective_usd: Optional[Decimal] = Field(default=None, description="Raw unclipped difference base - pert")
    is_exact: bool = Field(..., description="True if and only if both solves proved mathematical OPTIMAL with full audit pass")
    status: ShadowPriceStatus
    baseline_status: SolverStatus
    perturbed_status: SolverStatus
    objective_coverage: str = Field(default="PARTIAL_CONFIGURED")
    reason: Optional[str] = None
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BayHourPriceSurface(BaseModel):
    """Discrete valuation surface mapping bay capacity across discrete workshop intervals."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    rooftop_id: str = Field(..., min_length=1)
    snapshot_hash: str = Field(..., min_length=1)
    points: List[BayHourShadowPrice] = Field(default_factory=list)
    stride_ticks: int = Field(default=12, ge=1)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
