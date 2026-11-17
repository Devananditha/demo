"""Configuration for ServiceYield AI Optimise Engine.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 3)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md
"""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class OptimiseConfig(BaseModel):
    """Engine solving configuration and economic objective parameters."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    time_budget_seconds: float = Field(default=2.5, gt=0.0, description="Solver execution time limit")
    num_workers: int = Field(default=4, ge=1, description="CP-SAT parallel search workers")
    deterministic_seed: int = Field(default=42, description="Random seed for bit-exact reproducibility")

    # Economic parameters (Assumptions Register A3 & S-MATH-01)
    labor_contribution_per_hour_usd: Decimal = Field(
        default=Decimal("120.00"),
        ge=Decimal("0.00"),
        description="A3: $120.00/hour ($10.00/tick) contribution per incremental sold labor hour",
    )
    lateness_penalty_per_minute_usd: Decimal = Field(
        default=Decimal("0.50"),
        ge=Decimal("0.00"),
        description="S-MATH-01: $0.50/minute ($2.50/tick) delivery promise lateness penalty",
    )
    blocked_bay_penalty_per_minute_usd: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="lambda_block: Optional idle bay holding penalty (defaults to 0.00 if unspecified)",
    )
    churn_penalty_per_move_usd: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="lambda_churn: Schedule churn penalty per reassignment",
    )

    # Operational grid bounds
    horizon_ticks: int = Field(default=288, ge=1, le=288, description="Total discrete 5-min ticks in daily horizon")
    horizon_start_tick: int = Field(default=96, ge=0, le=288, description="08:00 AM standard day start")
    horizon_end_tick: int = Field(default=204, ge=0, le=288, description="17:00 PM standard day end")
    overtime_cutoff_tick: int = Field(default=228, ge=0, le=288, description="19:00 PM authorized overtime limit")
    allow_emergency_overtime: bool = Field(default=False, description="Authorize dispatch beyond technician shift end")
    enable_t1_warm_start: bool = Field(default=True, description="Feed T1 constructive solution as hint to CP-SAT")
