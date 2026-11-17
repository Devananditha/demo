"""Pydantic v2 Models and Schemas for Predict Readiness Service.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 2: Module 1: Predict)
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.2: Calculate Readiness)
- Technical Report Section 6.1
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReadinessState(str, Enum):
    """The four canonical, non-overlapping operational readiness states."""
    READY = "READY"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class CalibrationStatus(str, Enum):
    """Predictive uncertainty and calibration confidence level."""
    UNCALIBRATED = "UNCALIBRATED"
    CALIBRATED_LIGHT = "CALIBRATED_LIGHT"
    CALIBRATED_FULL = "CALIBRATED_FULL"
    DEGRADED = "DEGRADED"


class QuantileInterval(BaseModel):
    """Empirical-Bayes predicted usable-ready time quantiles in discrete ticks."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    p10: int = Field(..., ge=0, le=288, description="10th percentile usable-ready tick")
    p50: int = Field(..., ge=0, le=288, description="50th percentile (median) usable-ready tick")
    p90: int = Field(..., ge=0, le=288, description="90th percentile usable-ready tick")

    @model_validator(mode="after")
    def validate_monotonicity(self) -> "QuantileInterval":
        if not (self.p10 <= self.p50 <= self.p90):
            raise ValueError(f"Quantile monotonicity violated: p10 ({self.p10}) <= p50 ({self.p50}) <= p90 ({self.p90}) must hold.")
        return self


class OperationalSlack(BaseModel):
    """Operational schedule slack between latest feasible start and usable-ready time."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    latest_feasible_start_tick: int = Field(..., le=288, description="Latest feasible start tick (can be negative if already overdue)")
    usable_ready_tick: Optional[int] = Field(default=None, ge=0, le=288)
    slack_ticks: Optional[int] = Field(default=None, description="Schedule buffer: LFS tick - usable ready tick")
    slack_minutes: Optional[int] = Field(default=None, description="slack_ticks * 5")
    slack_p10_ticks: Optional[int] = Field(default=None)
    slack_p50_ticks: Optional[int] = Field(default=None)
    slack_p90_ticks: Optional[int] = Field(default=None)
    evaluation_slack_ticks: Optional[int] = Field(default=None, description="Evaluation window: LFS tick - current evaluation tick")
    evaluation_slack_minutes: Optional[int] = Field(default=None, description="evaluation_slack_ticks * 5")


class RepairOrderAssessment(BaseModel):
    """Predictive readiness assessment record for a single Repair Order."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ro_id: str = Field(..., min_length=1)
    snapshot_hash: str = Field(..., min_length=1)
    state: ReadinessState = Field(..., description="Canonical 4-state readiness classification")
    reasons: List[str] = Field(default_factory=list, description="Machine-readable diagnostic reason codes")
    p_delay: float = Field(..., ge=0.0, le=1.0, description="Predicted probability of missing latest feasible start")
    usable_ready_ticks: Optional[QuantileInterval] = Field(default=None)
    slack: Optional[OperationalSlack] = Field(default=None)
    calibration_status: CalibrationStatus = Field(default=CalibrationStatus.UNCALIBRATED)
    data_freshness_seconds: int = Field(default=0, ge=0)
    has_recovery_alternative: bool = Field(default=False, description="Whether a viable alternative supplier offer exists to recover negative baseline slack")
    best_alternative_usable_tick: Optional[int] = Field(default=None, ge=0, le=288, description="Usable ready tick of best candidate supplier recovery offer")
    best_alternative_slack_minutes: Optional[int] = Field(default=None, description="Slack minutes achieved under best alternative supplier offer")
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DealershipReadinessReport(BaseModel):
    """Full workshop readiness assessment report across all active Repair Orders."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    rooftop_id: str = Field(..., min_length=1)
    snapshot_hash: str = Field(..., min_length=1)
    assessments: List[RepairOrderAssessment] = Field(default_factory=list)
    summary_counts: Dict[str, int] = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
