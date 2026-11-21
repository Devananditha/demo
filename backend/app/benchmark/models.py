"""Domain models and schemas for Phase 2 Optimisation Validation & Benchmarks.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BenchmarkScenarioType(str, Enum):
    NORMAL_OPERATIONS = "NORMAL_OPERATIONS"
    SPECIALISED_BAY_CONTENTION = "SPECIALISED_BAY_CONTENTION"
    PARTS_DELAY = "PARTS_DELAY"
    TECHNICIAN_SHORTAGE = "TECHNICIAN_SHORTAGE"
    COMPETING_RESERVATIONS = "COMPETING_RESERVATIONS"
    SATURATED_CAPACITY = "SATURATED_CAPACITY"
    NULL_CONTROL = "NULL_CONTROL"


class DispatchMethod(str, Enum):
    FIFO = "FIFO"
    EDF = "EDF"
    CPSAT = "CPSAT"
    STALLBREAKER = "STALLBREAKER"


class BenchmarkMetrics(BaseModel):
    """Observable metrics produced by each scheduling/dispatch method on a scenario."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    method: DispatchMethod
    gross_contribution_usd: Decimal = Field(..., description="Gross sold labor contribution sum(M_i - C_i)")
    weighted_lateness_penalty_usd: Decimal = Field(..., description="Lateness penalties in USD")
    total_weighted_lateness_ticks: int = Field(..., ge=0, description="Weighted lateness in 5-min ticks")
    lateness_minutes: int = Field(..., ge=0, description="Total lateness in minutes")
    on_time_delivery_rate: float = Field(..., ge=0.0, le=100.0, description="Percentage of ROs delivered on or before promise")
    technician_utilisation_rate: float = Field(..., ge=0.0, le=100.0, description="Technician productive time / available time %")
    bay_utilisation_rate: float = Field(..., ge=0.0, le=100.0, description="Service bay active time / operating window %")
    workshop_idle_minutes: int = Field(..., ge=0, description="Total bay idle minutes during operating horizon")
    recovery_plan_churn: int = Field(default=0, ge=0, description="Task assignment / sequencing changes from initial plan")
    solve_time_ms: float = Field(..., ge=0.0, description="Algorithm execution latency in milliseconds")
    constraint_violations: int = Field(default=0, ge=0, description="Total C1-C7 violations (must be identically 0)")
    is_verified: bool = Field(default=True, description="Certified PASS by independent L4 sweep-line oracle")
    is_fully_certified: bool = Field(default=True, description="Certified PASS by supplemental audit oracle")
    net_objective_usd: Decimal = Field(..., description="Net economic yield Z = Gross - Lateness - Sourcing - Idle")


class ScenarioBenchmarkResult(BaseModel):
    """Benchmark outcome for a single scenario across all 4 dispatch methods."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    scenario_id: str
    scenario_type: BenchmarkScenarioType
    title: str
    description: str
    seed: int
    methods: Dict[str, BenchmarkMetrics]
    stallbreaker_advantage_usd: Decimal = Field(..., description="Delta Z StallBreaker vs Best Baseline")
    replay_record_id: Optional[str] = None


class StatisticalMetricSummary(BaseModel):
    """Paired statistical summary across random seeds."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    metric_name: str
    baseline_mean: float
    stallbreaker_mean: float
    mean_delta: float
    pct_improvement: float
    ci_95_lower: float
    ci_95_upper: float
    p_value: float
    is_statistically_significant: bool


class BenchmarkSuiteReport(BaseModel):
    """Complete multi-scenario, multi-method benchmark suite report."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    benchmark_id: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scenarios: List[ScenarioBenchmarkResult]
    statistical_summaries: List[StatisticalMetricSummary]
    total_scenarios_evaluated: int
    all_violations_zero: bool
