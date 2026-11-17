"""Four-State Service Readiness Classifier for ServiceYield AI.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 2: Module 1: Predict)
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.2: Calculate Readiness)
- Technical Report Section 6.1 (Module 1: Predict)

State Hierarchy & Strict Precedence:
  1. UNKNOWN:  Missing, stale, or untrusted telemetry (fails closed).
  2. BLOCKED:  Hard operational gate unsatisfied (backordered part with no ETA, no qualified tech).
  3. AT_RISK:  Operational slack < 30m, P(delay) > tau_raise (0.25), or in-transit parts risk.
  4. READY:    All hard requirements satisfied with adequate operational slack (>= 30m).
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.predict.engine import EmpiricalBayesQuantileEngine
from app.predict.models import (
    CalibrationStatus,
    DealershipReadinessReport,
    QuantileInterval,
    ReadinessState,
    RepairOrderAssessment,
)
from app.predict.slack import (
    SLACK_AT_RISK_THRESHOLD_TICKS,
    SLACK_BLOCKED_THRESHOLD_TICKS,
    TAU_RAISE,
    SlackAnalyzer,
)
from app.schemas.domain import DealershipSnapshotSchema, RepairOrderSchema


class PredictReadinessClassifier:
    """Evaluates canonical workshop state and classifies repair orders into 4 readiness states."""

    def __init__(
        self,
        quantile_engine: Optional[EmpiricalBayesQuantileEngine] = None,
        max_freshness_seconds: int = 86400,
        tau_raise: float = TAU_RAISE,
    ):
        self.quantile_engine = quantile_engine or EmpiricalBayesQuantileEngine()
        self.max_freshness_seconds = max_freshness_seconds
        self.tau_raise = tau_raise

    def assess_repair_order(
        self,
        ro: RepairOrderSchema,
        snapshot: DealershipSnapshotSchema,
        current_tick: Optional[int] = None,
        now_utc: Optional[datetime] = None,
    ) -> RepairOrderAssessment:
        """Classifies a single Repair Order using the canonical 4-state precedence rules."""
        now = now_utc or datetime.now(timezone.utc)
        reasons: List[str] = []

        # Associated tasks and parts for this RO
        ro_tasks = [t for t in snapshot.tasks if t.ro_id == ro.ro_id]
        ro_parts = [p for p in snapshot.part_requirements if p.ro_id == ro.ro_id]
        ro_offers = [
            o for o in snapshot.supplier_offers
            if any(o.part_req_id == p.part_req_id for p in ro_parts)
        ]

        # Calculate data freshness
        updated_at = ro.updated_at if ro.updated_at.tzinfo else ro.updated_at.replace(tzinfo=timezone.utc)
        freshness_seconds = max(0, int((now - updated_at).total_seconds()))

        # ====================================================================
        # STEP 1: UNKNOWN CHECK (Fail-Closed Telemetry Validation)
        # ====================================================================
        # Check telemetry staleness
        if freshness_seconds > self.max_freshness_seconds:
            reasons.append("STALE_TELEMETRY_DATA")
            return RepairOrderAssessment(
                ro_id=ro.ro_id,
                snapshot_hash=snapshot.snapshot_hash or "",
                state=ReadinessState.UNKNOWN,
                reasons=reasons,
                p_delay=1.0,
                calibration_status=CalibrationStatus.UNCALIBRATED,
                data_freshness_seconds=freshness_seconds,
                computed_at=now,
            )

        # Check critical fields
        if not ro.complaint or not ro.promised_at or ro.promise_tick is None:
            reasons.append("CRITICAL_TELEMETRY_MISSING")
            return RepairOrderAssessment(
                ro_id=ro.ro_id,
                snapshot_hash=snapshot.snapshot_hash or "",
                state=ReadinessState.UNKNOWN,
                reasons=reasons,
                p_delay=1.0,
                calibration_status=CalibrationStatus.UNCALIBRATED,
                data_freshness_seconds=freshness_seconds,
                computed_at=now,
            )

        # Unknown vehicle physical state
        physical_state_str = ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state)
        if physical_state_str == "UNKNOWN":
            reasons.append("UNKNOWN_VEHICLE_PHYSICAL_STATE")
            return RepairOrderAssessment(
                ro_id=ro.ro_id,
                snapshot_hash=snapshot.snapshot_hash or "",
                state=ReadinessState.UNKNOWN,
                reasons=reasons,
                p_delay=1.0,
                calibration_status=CalibrationStatus.UNCALIBRATED,
                data_freshness_seconds=freshness_seconds,
                computed_at=now,
            )

        # ====================================================================
        # STEP 2: HARD GATE VALIDATION (C1 Skills/Bays & Backordered Parts)
        # ====================================================================
        # C1 Skills available in rooftop
        all_skills = {
            skill
            for tech in snapshot.technicians
            if tech.is_active
            for skill in tech.skill_certifications
        }
        for task in ro_tasks:
            if task.required_skill not in all_skills:
                reasons.append(f"UNAVAILABLE_TECHNICIAN_SKILL_{task.required_skill}")

        # C1 Bay types available in rooftop
        operational_bay_types = {b.bay_type for b in snapshot.bays if b.is_operational}
        for task in ro_tasks:
            if task.required_bay_type not in operational_bay_types:
                reasons.append(f"UNAVAILABLE_BAY_TYPE_{task.required_bay_type}")

        # Parts hard-gate: Backordered parts with no usable ready tick and no candidate supplier offers
        for part in ro_parts:
            status_str = part.inventory_status.value if hasattr(part.inventory_status, "value") else str(part.inventory_status)
            if status_str == "BACKORDERED" and part.usable_ready_tick is None:
                # Check if an alternative supplier offer exists
                part_offers = [o for o in ro_offers if o.part_req_id == part.part_req_id]
                if not part_offers:
                    reasons.append("PART_BACKORDERED_NO_ETA")

        # If any hard operational gate failed, mark BLOCKED immediately
        if reasons:
            return RepairOrderAssessment(
                ro_id=ro.ro_id,
                snapshot_hash=snapshot.snapshot_hash or "",
                state=ReadinessState.BLOCKED,
                reasons=reasons,
                p_delay=1.0,
                usable_ready_ticks=None,
                slack=None,
                calibration_status=CalibrationStatus.UNCALIBRATED,
                data_freshness_seconds=freshness_seconds,
                computed_at=now,
            )

        # ====================================================================
        # STEP 3: SLACK CALCULATION & EMPIRICAL-BAYES ESTIMATION
        # ====================================================================
        # Calculate Latest Feasible Start (LFS)
        lfs_tick = SlackAnalyzer.calculate_latest_feasible_start(ro, ro_tasks)

        # Determine effective usable-ready tick for parts
        # If parts are required, find the latest usable-ready tick across required parts
        latest_usable_ready_tick: Optional[int] = None
        has_in_transit_part: bool = False
        supplier_id_for_delay: Optional[str] = None

        if ro_parts:
            for part in ro_parts:
                status_str = part.inventory_status.value if hasattr(part.inventory_status, "value") else str(part.inventory_status)
                if status_str == "IN_TRANSIT":
                    has_in_transit_part = True
                
                u_tick = part.usable_ready_tick
                # If part has supplier offers, select the earliest usable offer if part has no tick
                if u_tick is None:
                    part_offers = [o for o in ro_offers if o.part_req_id == part.part_req_id]
                    if part_offers:
                        best_offer = min(part_offers, key=lambda o: o.usable_ready_tick)
                        u_tick = best_offer.usable_ready_tick
                        supplier_id_for_delay = best_offer.supplier_id

                if u_tick is not None:
                    latest_usable_ready_tick = max(latest_usable_ready_tick or 0, u_tick)
        else:
            # No parts required: ready at start of operating day (or current tick)
            latest_usable_ready_tick = current_tick or snapshot.rooftop.operating_day_start_tick

        # Compute empirical-Bayes quantiles and delay probability
        quantiles: Optional[QuantileInterval] = None
        calibration_status = CalibrationStatus.UNCALIBRATED
        p_delay = 0.0

        if latest_usable_ready_tick is not None:
            quantiles, calibration_status = self.quantile_engine.estimate_usable_ready_quantiles(
                base_usable_ready_tick=latest_usable_ready_tick,
                supplier_id=supplier_id_for_delay,
            )
            p_delay = self.quantile_engine.compute_delay_probability(
                base_usable_ready_tick=latest_usable_ready_tick,
                latest_feasible_start_tick=lfs_tick,
                supplier_id=supplier_id_for_delay,
            )

        # Compute operational slack
        slack = SlackAnalyzer.compute_slack(
            latest_feasible_start_tick=lfs_tick,
            usable_ready_tick=latest_usable_ready_tick,
            quantiles=quantiles,
        )

        # ====================================================================
        # STEP 4: AT_RISK VS READY CLASSIFICATION
        # ====================================================================
        # Condition A: Negative slack with alternative supplier options (e.g. RO-104 with Hotshot alternative)
        # Condition B: Operational slack < 30 minutes (6 ticks)
        # Condition C: P(delay) > tau_raise (0.25)
        # Condition D: Vehicle is IMMOBILIZED_ON_LIFT with parts in transit
        # Condition E: Parts in transit facing courier lead-time variance

        is_at_risk = False

        if slack.slack_ticks is not None and slack.slack_ticks < SLACK_AT_RISK_THRESHOLD_TICKS:
            is_at_risk = True
            reasons.append("SLACK_BELOW_30_MINUTES")

        if p_delay > self.tau_raise:
            is_at_risk = True
            reasons.append(f"DELAY_PROBABILITY_EXCEEDS_THRESHOLD_{p_delay:.2f}")

        if has_in_transit_part:
            is_at_risk = True
            reasons.append("PARTS_IN_TRANSIT_LEAD_TIME_RISK")

        if physical_state_str == "IMMOBILIZED_ON_LIFT" and (has_in_transit_part or (ro.status.value if hasattr(ro.status, "value") else str(ro.status)) == "STALLED"):
            is_at_risk = True
            reasons.append("VEHICLE_IMMOBILIZED_ON_LIFT_STALLED")

        # If primary baseline slack is severely negative (< 0) and has NO candidate alternatives at all:
        if slack.slack_ticks is not None and slack.slack_ticks < SLACK_BLOCKED_THRESHOLD_TICKS:
            # Check if any candidate supplier offer can achieve non-negative slack
            has_viable_alternative = False
            for offer in ro_offers:
                alt_slack = lfs_tick - offer.usable_ready_tick
                if alt_slack >= 0:
                    has_viable_alternative = True
                    break
            
            if not has_viable_alternative:
                reasons.append("NEGATIVE_SLACK_UNRECOVERABLE")
                return RepairOrderAssessment(
                    ro_id=ro.ro_id,
                    snapshot_hash=snapshot.snapshot_hash or "",
                    state=ReadinessState.BLOCKED,
                    reasons=reasons,
                    p_delay=1.0,
                    usable_ready_ticks=quantiles,
                    slack=slack,
                    calibration_status=calibration_status,
                    data_freshness_seconds=freshness_seconds,
                    computed_at=now,
                )

        if is_at_risk:
            return RepairOrderAssessment(
                ro_id=ro.ro_id,
                snapshot_hash=snapshot.snapshot_hash or "",
                state=ReadinessState.AT_RISK,
                reasons=reasons,
                p_delay=p_delay,
                usable_ready_ticks=quantiles,
                slack=slack,
                calibration_status=calibration_status,
                data_freshness_seconds=freshness_seconds,
                computed_at=now,
            )

        # Otherwise READY
        reasons.append("ALL_HARD_REQUIREMENTS_SATISFIED")
        return RepairOrderAssessment(
            ro_id=ro.ro_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            state=ReadinessState.READY,
            reasons=reasons,
            p_delay=p_delay,
            usable_ready_ticks=quantiles,
            slack=slack,
            calibration_status=calibration_status,
            data_freshness_seconds=freshness_seconds,
            computed_at=now,
        )

    def assess_dealership_readiness(
        self,
        snapshot: DealershipSnapshotSchema,
        current_tick: Optional[int] = None,
        now_utc: Optional[datetime] = None,
    ) -> DealershipReadinessReport:
        """Evaluates readiness for all active Repair Orders in the dealership snapshot."""
        now = now_utc or datetime.now(timezone.utc)
        assessments: List[RepairOrderAssessment] = []
        summary_counts: Dict[str, int] = defaultdict(int)

        for ro in snapshot.repair_orders:
            assessment = self.assess_repair_order(
                ro=ro,
                snapshot=snapshot,
                current_tick=current_tick,
                now_utc=now,
            )
            assessments.append(assessment)
            summary_counts[assessment.state.value] += 1

        return DealershipReadinessReport(
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            assessments=assessments,
            summary_counts=dict(summary_counts),
            computed_at=now,
        )
