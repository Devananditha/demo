"""Domain Models for Decision Replay and Explainability in ServiceYield AI.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DecisionReplayDiff(BaseModel):
    """Calculated operational and economic delta between baseline and proposed schedules."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    baseline_plan_id: str = Field(..., description="Identifier of unmitigated baseline plan")
    proposed_plan_id: str = Field(..., description="Identifier of proposed candidate/recovery plan")

    # Financial metrics and deltas
    baseline_gross_contribution_usd: Decimal = Field(default=Decimal("0.00"))
    proposed_gross_contribution_usd: Decimal = Field(default=Decimal("0.00"))
    delta_gross_contribution_usd: Decimal = Field(default=Decimal("0.00"), description="Proposed - Baseline gross labor contribution")

    sourcing_freight_usd: Decimal = Field(default=Decimal("0.00"), description="Expedited courier freight surcharge")
    rescheduling_churn_cost_usd: Decimal = Field(default=Decimal("0.00"), description="Disruption friction / schedule churn cost")

    baseline_net_objective_usd: Decimal = Field(default=Decimal("0.00"))
    proposed_net_objective_usd: Decimal = Field(default=Decimal("0.00"))
    net_economic_delta_usd: Decimal = Field(default=Decimal("0.00"), description="Net economic difference Z_prop - Z_base in USD")

    # Operational metrics and deltas
    baseline_weighted_lateness_ticks: int = Field(default=0, ge=0)
    proposed_weighted_lateness_ticks: int = Field(default=0, ge=0)
    delta_weighted_lateness_ticks: int = Field(default=0, description="Proposed - Baseline weighted lateness (negative indicates improvement)")

    baseline_bay_utilization_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    proposed_bay_utilization_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    delta_bay_utilization_pct: float = Field(default=0.0, description="Change in physical bay active utilization percentage")

    baseline_idle_minutes: int = Field(default=0, ge=0)
    proposed_idle_minutes: int = Field(default=0, ge=0)
    delta_idle_minutes: int = Field(default=0, description="Change in avoidable blocked/idle bay minutes")

    # Constraint and certification integrity
    baseline_constraint_violations: int = Field(default=0, ge=0)
    proposed_constraint_violations: int = Field(default=0, ge=0)
    is_verified: bool = Field(default=False, description="L4 Sweep-Line geometric verification status")
    is_fully_certified: bool = Field(default=False, description="L4 and Supplemental dual audit certification")


class DecisionExplainability(BaseModel):
    """Structured decision explanation providing human-interpretable operational reasoning."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    recommendation_summary: str = Field(..., description="Executive plain-language recommendation summary")
    primary_driver: str = Field(..., description="Core operational factor driving the recommendation")
    constraints_considered: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of formal C1–C7 constraints evaluated with compliance evidence",
    )
    objective_breakdown: Dict[str, str] = Field(
        default_factory=dict,
        description="Itemized economic objective components in formatted currency",
    )
    alternatives_rejected: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rejected or pruned alternatives with technical rejection reasons",
    )
    unresolved_risks: List[str] = Field(
        default_factory=list,
        description="Remaining operational or parts delivery risks",
    )


class DecisionReplayRecord(BaseModel):
    """Complete persisted Decision Replay entry for auditability and retrospective replay."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    replay_id: str = Field(..., min_length=1)
    rooftop_id: str = Field(..., min_length=1)
    snapshot_hash: str = Field(..., min_length=1)
    scenario_name: str = Field(default="S-MATH-01 Canonical Disruption Replay")
    diff: DecisionReplayDiff
    explainability: DecisionExplainability
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
