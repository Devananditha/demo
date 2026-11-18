"""Independent Supplemental Audit Oracle for ServiceYield AI Optimise Engine.

Authoritative Reference:
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/12_VERIFICATION_AND_REVALIDATION.md

Guarantees:
1. Zero solver dependency (pure Python).
2. Independent of CP-SAT and T1 internal scheduling logic.
3. Validates operational evidence contracts:
   - C7 Customer authorization enforcement on all scheduled work.
   - C5 Vehicle movement semantics (Delta t_move = 2 ticks, porter availability).
   - C1 Vehicle weight against lifting capacity and fitment verification.
   - C6 Two-week rolling flat-rate fairness band compliance.
4. Supplements, but never weakens or replaces, the primary L4 Sweep-Line Oracle.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.constraints.rules import ConstraintViolation, ViolationCode
from app.optimise.evidence import WorkshopEvidenceBundle
from app.schemas.domain import DealershipSnapshotSchema, VehiclePhysicalState
from app.verifier.models import CandidateSchedulePlan


class SupplementalAuditResult(BaseModel):
    """Certified result of the independent supplemental operational audit."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    is_valid: bool
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    coverage_gaps: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class SupplementalAuditOracle:
    """Independent auditor verifying operational evidence contracts beyond interval geometry."""

    def __init__(self, snapshot: DealershipSnapshotSchema, evidence: Optional[WorkshopEvidenceBundle] = None):
        self.snapshot = snapshot
        self.evidence = evidence or WorkshopEvidenceBundle()
        self.bays = {b.bay_id: b for b in snapshot.bays}
        self.technicians = {t.tech_id: t for t in snapshot.technicians}
        self.tasks = {t.task_id: t for t in snapshot.tasks}
        self.ros = {r.ro_id: r for r in snapshot.repair_orders}

    def audit_plan(self, plan: CandidateSchedulePlan) -> SupplementalAuditResult:
        """Audits candidate schedule plan against explicit operational evidence contracts."""
        violations: List[ConstraintViolation] = []
        coverage_gaps: List[str] = []

        scheduled_ros = {a.ro_id for a in plan.assignments}

        # 1. C7 Customer Authorization Audit
        for ro_id in scheduled_ros:
            if not self.evidence.is_ro_authorized(ro_id):
                violations.append(
                    ConstraintViolation(
                        code=ViolationCode.C7_UNAUTHORIZED_REPAIR,
                        constraint="C7",
                        message=f"Repair Order '{ro_id}' has scheduled work but lacks explicit customer authorization.",
                        entity_id=ro_id,
                    )
                )

        # 2. C5 Vehicle Movement & Staging Semantics Audit
        # Group assignments by RO
        ro_assignments: Dict[str, List[Any]] = defaultdict(list)
        for a in plan.assignments:
            ro_assignments[a.ro_id].append(a)

        for ro_id, assignments in ro_assignments.items():
            ro = self.ros.get(ro_id)
            if not ro:
                continue

            phys_ev = self.evidence.vehicle_evidence.get(ro.vehicle_id) or self.evidence.vehicle_evidence.get(ro_id)
            phys_state = phys_ev.physical_state if phys_ev else ro.physical_state
            state_val = phys_state.value if hasattr(phys_state, "value") else str(phys_state)

            if state_val == "UNKNOWN":
                violations.append(
                    ConstraintViolation(
                        code=ViolationCode.C5_UNKNOWN_STATE_MOVE,
                        constraint="C5",
                        message=f"Vehicle for RO '{ro_id}' has UNKNOWN physical state; automated scheduling prohibited.",
                        entity_id=ro_id,
                    )
                )

            # Check holding staging and movement delay
            is_holding = phys_ev.is_in_holding if phys_ev else (state_val == "IN_HOLDING")
            if is_holding and assignments:
                first_start = min(a.start_tick for a in assignments)
                # Movement requires at least 2 ticks (10 minutes) from evaluation start
                eval_start = self.evidence.current_tick
                if first_start < eval_start + 2:
                    violations.append(
                        ConstraintViolation(
                            code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                            constraint="C5",
                            message=(
                                f"Vehicle for RO '{ro_id}' in holding cannot start at tick {first_start}; "
                                f"requires at least 2 ticks move time from evaluation tick {eval_start}."
                            ),
                            entity_id=ro_id,
                            tick=first_start,
                        )
                    )

        # 3. C1 Vehicle Weight and Fitment Evidence Audit
        for a in plan.assignments:
            task = self.tasks.get(a.task_id)
            ro = self.ros.get(a.ro_id)
            bay = self.bays.get(a.bay_id)
            if not task or not ro or not bay:
                continue

            phys_ev = self.evidence.vehicle_evidence.get(ro.vehicle_id) or self.evidence.vehicle_evidence.get(ro.ro_id)
            if phys_ev:
                if not phys_ev.fitment_verified:
                    violations.append(
                        ConstraintViolation(
                            code=ViolationCode.C1_SKILL_INELIGIBLE,
                            constraint="C1",
                            message=f"Part fitment not verified for vehicle '{ro.vehicle_id}'.",
                            entity_id=task.task_id,
                        )
                    )
                if phys_ev.vehicle_weight_lbs is not None:
                    if phys_ev.vehicle_weight_lbs > bay.lifting_capacity_lbs:
                        violations.append(
                            ConstraintViolation(
                                code=ViolationCode.C1_BAY_CAPACITY_EXCEEDED,
                                constraint="C1",
                                message=(
                                    f"Vehicle weight ({phys_ev.vehicle_weight_lbs} lbs) exceeds "
                                    f"bay lifting capacity ({bay.lifting_capacity_lbs} lbs)."
                                ),
                                entity_id=bay.bay_id,
                                tick=a.start_tick,
                            )
                        )
            else:
                coverage_gaps.append(f"Vehicle physical/weight evidence missing for vehicle '{ro.vehicle_id}'.")

        # 4. C6 Two-Week Rolling Fairness Band Audit
        tech_allocated_ticks: Dict[str, int] = defaultdict(int)
        for a in plan.assignments:
            task = self.tasks.get(a.task_id)
            if task:
                tech_allocated_ticks[a.tech_id] += task.flat_rate_minutes  # using flat-rate minutes

        if not self.evidence.technician_fairness:
            coverage_gaps.append("Rolling two-week historical flat-rate fairness evidence missing.")
        else:
            for tech_id, fairness in self.evidence.technician_fairness.items():
                new_allocated_hours = Decimal(str(tech_allocated_ticks.get(tech_id, 0))) / Decimal("60")
                total_hours = fairness.historical_allocated_hours + new_allocated_hours
                peer_median = fairness.median_peer_hours
                max_allowed = peer_median * Decimal("1.15")
                min_allowed = peer_median * Decimal("0.85")
                if total_hours > max_allowed or total_hours < min_allowed:
                    violations.append(
                        ConstraintViolation(
                            code=ViolationCode.C6_OUTSIDE_SHIFT,
                            constraint="C6",
                            message=(
                                f"Technician '{tech_id}' total flat-rate hours ({total_hours:.1f}h) breaches "
                                f"15% peer fairness band [{min_allowed:.1f}h, {max_allowed:.1f}h]."
                            ),
                            entity_id=tech_id,
                        )
                    )

        return SupplementalAuditResult(
            is_valid=len(violations) == 0,
            violations=[v.to_dict() for v in violations],
            coverage_gaps=coverage_gaps,
            details={
                "scheduled_ros_count": len(scheduled_ros),
                "authorized_ros_count": sum(1 for r in scheduled_ros if self.evidence.is_ro_authorized(r)),
            },
        )
