"""Independent Supplemental Audit Oracle for ServiceYield AI Optimise Engine.

Authoritative Reference:
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/12_VERIFICATION_AND_REVALIDATION.md

Guarantees:
1. Zero solver dependency (pure Python).
2. Independent of CP-SAT and T1 internal scheduling logic.
3. Validates operational evidence contracts:
   - C7 Customer authorization enforcement on all scheduled work.
   - C5 Vehicle movement semantics (Delta t_move = 2 ticks, porter availability, arrival confirmation).
   - C1 Vehicle weight against lifting capacity and fitment verification.
   - C6 Two-week rolling flat-rate fairness band compliance across all assigned technicians.
   - Work-in-progress locked assignments and remaining duration telemetry.
4. Supplements, but never weakens or replaces, the primary L4 Sweep-Line Oracle.
"""

from collections import defaultdict
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.constraints.rules import ConstraintViolation, ViolationCode
from app.optimise.evidence import WorkshopEvidenceBundle
from app.schemas.domain import DealershipSnapshotSchema, VehiclePhysicalState
from app.verifier.models import CandidateSchedulePlan


class CertificationStatus(str, Enum):
    """Rigorous operational evidence certification outcome."""
    VALID_AND_CERTIFIED = "VALID_AND_CERTIFIED"
    INVALID_VIOLATIONS = "INVALID_VIOLATIONS"
    INCOMPLETE_EVIDENCE = "INCOMPLETE_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NO_WORK_REMAINING = "NO_WORK_REMAINING"


class SupplementalAuditResult(BaseModel):
    """Certified result of the independent supplemental operational audit."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    is_valid: bool = Field(..., description="True only if zero violations AND no blocking mandatory evidence gaps")
    certification_status: CertificationStatus
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    coverage_gaps: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    is_actionable: bool = Field(default=False, description="True only if certified valid, zero coverage gaps, and non-empty plan")


class SupplementalAuditOracle:
    """Independent auditor verifying operational evidence contracts beyond interval geometry."""

    def __init__(self, snapshot: DealershipSnapshotSchema, evidence: Optional[WorkshopEvidenceBundle] = None):
        self.snapshot = snapshot
        self.evidence = evidence or WorkshopEvidenceBundle()
        self.bays = {b.bay_id: b for b in snapshot.bays}
        self.technicians = {t.tech_id: t for t in snapshot.technicians}
        self.tasks = {t.task_id: t for t in snapshot.tasks}
        self.ros = {r.ro_id: r for r in snapshot.repair_orders}

    def audit_plan(
        self,
        plan: CandidateSchedulePlan,
        planned_movements: Optional[List[Any]] = None,
    ) -> SupplementalAuditResult:
        """Audits candidate schedule plan against explicit operational evidence contracts."""
        violations: List[ConstraintViolation] = []
        coverage_gaps: List[str] = []

        if not plan.assignments:
            has_incomplete = any(
                (t.status.value if hasattr(t.status, "value") else str(t.status)) != "COMPLETED"
                for t in self.snapshot.tasks
            )
            if has_incomplete:
                return SupplementalAuditResult(
                    is_valid=False,
                    certification_status=CertificationStatus.INCOMPLETE_EVIDENCE,
                    violations=[],
                    coverage_gaps=["Empty schedule plan produced while incomplete repair orders remain in snapshot."],
                    is_actionable=False,
                    details={"reason": "Empty plan with work remaining is neither certified nor actionable"},
                )
            else:
                return SupplementalAuditResult(
                    is_valid=True,
                    certification_status=CertificationStatus.NO_WORK_REMAINING,
                    violations=[],
                    coverage_gaps=[],
                    is_actionable=False,
                    details={"reason": "All work is already completed; explicit no-op state", "no_work_remaining": True},
                )

        scheduled_ros = {a.ro_id for a in plan.assignments}
        scheduled_tech_ids = {a.tech_id for a in plan.assignments}
        movements: List[Any] = list(planned_movements or getattr(plan, "planned_movements", []) or [])

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

        # 2. C5 Vehicle Movement, Physical State & Staging Semantics Audit
        ro_assignments: Dict[str, List[Any]] = defaultdict(list)
        for a in plan.assignments:
            ro_assignments[a.ro_id].append(a)

        planned_moves_by_ro: Dict[str, List[Any]] = defaultdict(list)
        for m in movements:
            m_ro = getattr(m, "ro_id", None)
            if m_ro:
                planned_moves_by_ro[m_ro].append(m)

        for ro_id, assignments in ro_assignments.items():
            ro = self.ros.get(ro_id)
            if not ro:
                continue

            phys_ev = self.evidence.get_vehicle_physical_evidence(ro.vehicle_id, ro_id)
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

            # Check holding lot staging and movement delay
            is_holding = phys_ev.is_in_holding if phys_ev else (state_val == "IN_HOLDING")
            if is_holding and assignments:
                first_start = min(a.start_tick for a in assignments)
                first_bay = next(a.bay_id for a in assignments if a.start_tick == first_start)
                eval_start = self.evidence.current_tick

                ro_moves = planned_moves_by_ro.get(ro_id, [])
                if not ro_moves:
                    violations.append(
                        ConstraintViolation(
                            code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                            constraint="C5",
                            message=f"Vehicle for RO '{ro_id}' was IN_HOLDING but lacks an explicit planned movement operation.",
                            entity_id=ro_id,
                            tick=first_start,
                        )
                    )
                else:
                    for m in ro_moves:
                        m_start = getattr(m, "start_tick", None)
                        m_end = getattr(m, "end_tick", None)
                        m_res = getattr(m, "assigned_resource_id", None)
                        m_target = getattr(m, "target_bay_id", None)
                        m_dur = (m_end - m_start) if (m_start is not None and m_end is not None) else 0

                        if m_dur != 2:
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                                    constraint="C5",
                                    message=f"Planned movement for RO '{ro_id}' has duration {m_dur} ticks; must be exactly 2 ticks.",
                                    entity_id=ro_id,
                                    tick=m_start,
                                )
                            )

                        if m_start is not None and m_start < eval_start:
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                                    constraint="C5",
                                    message=f"Planned movement for RO '{ro_id}' starts at tick {m_start} before evaluation tick {eval_start}.",
                                    entity_id=ro_id,
                                    tick=m_start,
                                )
                            )

                        if m_end is not None and m_end > first_start:
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                                    constraint="C5",
                                    message=f"Planned movement for RO '{ro_id}' finishes at tick {m_end} after first mechanical task start {first_start}.",
                                    entity_id=ro_id,
                                    tick=m_end,
                                )
                            )

                        if m_target != first_bay:
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                                    constraint="C5",
                                    message=f"Planned movement destination bay '{m_target}' does not match scheduled task bay '{first_bay}'.",
                                    entity_id=ro_id,
                                )
                            )

                        if m_res not in self.evidence.available_porter_tech_ids and m_res not in self.technicians:
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                                    constraint="C5",
                                    message=f"Planned movement resource '{m_res}' for RO '{ro_id}' is not an authorized or available resource.",
                                    entity_id=ro_id,
                                )
                            )

            # Check MOVE_PENDING state semantics
            if state_val == "MOVE_PENDING":
                move_ev = self.evidence.vehicle_movements.get(ro.vehicle_id) or self.evidence.vehicle_movements.get(ro_id)
                if not move_ev or not move_ev.arrival_confirmed:
                    violations.append(
                        ConstraintViolation(
                            code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                            constraint="C5",
                            message=f"Vehicle for RO '{ro_id}' in MOVE_PENDING lacks arrival confirmation at destination bay.",
                            entity_id=ro_id,
                        )
                    )

            # Check IMMOBILIZED_ON_LIFT relocation prevention
            if state_val == "IMMOBILIZED_ON_LIFT":
                assigned_bay = (phys_ev.current_bay_id if phys_ev else None) or ro.assigned_bay_id
                if not assigned_bay:
                    violations.append(
                        ConstraintViolation(
                            code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                            constraint="C5",
                            message=f"Vehicle for RO '{ro_id}' is IMMOBILIZED_ON_LIFT but lacks assigned bay evidence.",
                            entity_id=ro_id,
                        )
                    )
                else:
                    for a in assignments:
                        if a.bay_id != assigned_bay:
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                                    constraint="C5",
                                    message=(
                                        f"Vehicle for RO '{ro_id}' is immobilized on bay '{assigned_bay}'; "
                                        f"cannot be scheduled on bay '{a.bay_id}'."
                                    ),
                                    entity_id=ro_id,
                                    tick=a.start_tick,
                                )
                            )
                if planned_moves_by_ro.get(ro_id):
                    violations.append(
                        ConstraintViolation(
                            code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                            constraint="C5",
                            message=f"Vehicle for RO '{ro_id}' is IMMOBILIZED_ON_LIFT; movement operation is prohibited.",
                            entity_id=ro_id,
                        )
                    )

        # Resource exclusivity across planned movements
        for i in range(len(movements)):
            m1 = movements[i]
            m1_s = getattr(m1, "start_tick", None)
            m1_e = getattr(m1, "end_tick", None)
            m1_res = getattr(m1, "assigned_resource_id", None)
            if m1_s is None or m1_e is None or not m1_res:
                continue

            for j in range(i + 1, len(movements)):
                m2 = movements[j]
                m2_res = getattr(m2, "assigned_resource_id", None)
                if m1_res == m2_res:
                    m2_s = getattr(m2, "start_tick", None)
                    m2_e = getattr(m2, "end_tick", None)
                    if m2_s is not None and m2_e is not None:
                        if max(m1_s, m2_s) < min(m1_e, m2_e):
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                                    constraint="C5",
                                    message=f"Movement resource '{m1_res}' has overlapping movements [{m1_s}, {m1_e}) and [{m2_s}, {m2_e}).",
                                    entity_id=m1_res,
                                    tick=max(m1_s, m2_s),
                                )
                            )

            if m1_res in self.technicians:
                tech = self.technicians[m1_res]
                for a in plan.assignments:
                    if a.tech_id == m1_res:
                        if max(m1_s, a.start_tick) < min(m1_e, a.end_tick):
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C4_TECH_DOUBLE_BOOKED,
                                    constraint="C4",
                                    message=f"Technician '{m1_res}' movement [{m1_s}, {m1_e}) overlaps assigned mechanical task '{a.task_id}' [{a.start_tick}, {a.end_tick}).",
                                    entity_id=m1_res,
                                    tick=max(m1_s, a.start_tick),
                                )
                            )
                l_start = tech.lunch_start_tick
                l_end = l_start + tech.lunch_duration_ticks
                if max(m1_s, l_start) < min(m1_e, l_end):
                    violations.append(
                        ConstraintViolation(
                            code=ViolationCode.C6_BREAK_WINDOW_BREACH,
                            constraint="C6",
                            message=f"Technician '{m1_res}' movement [{m1_s}, {m1_e}) overlaps mandatory lunch [{l_start}, {l_end}).",
                            entity_id=m1_res,
                            tick=max(m1_s, l_start),
                        )
                    )

        # 3. C1 Vehicle Weight, Bay Lifting Capacity, and Fitment Evidence Audit
        for a in plan.assignments:
            task = self.tasks.get(a.task_id)
            ro = self.ros.get(a.ro_id)
            bay = self.bays.get(a.bay_id)
            if not task or not ro or not bay:
                continue

            phys_ev = self.evidence.get_vehicle_physical_evidence(ro.vehicle_id, ro.ro_id)
            if phys_ev is None:
                coverage_gaps.append(
                    f"Vehicle physical/weight evidence completely missing for vehicle '{ro.vehicle_id}' (RO '{ro.ro_id}')."
                )
                continue

            # Fitment verification check (Fail closed if None or False)
            if phys_ev.fitment_verified is None:
                coverage_gaps.append(
                    f"Parts fitment verification evidence missing (unverified) for vehicle '{ro.vehicle_id}'."
                )
            elif phys_ev.fitment_verified is False:
                violations.append(
                    ConstraintViolation(
                        code=ViolationCode.C1_SKILL_INELIGIBLE,
                        constraint="C1",
                        message=f"Part fitment rejected as incompatible for vehicle '{ro.vehicle_id}'.",
                        entity_id=task.task_id,
                    )
                )

            # Vehicle weight check (Fail closed if missing)
            if phys_ev.vehicle_weight_lbs is None:
                coverage_gaps.append(
                    f"Vehicle weight evidence missing for vehicle '{ro.vehicle_id}'; cannot certify lifting capacity of bay '{bay.bay_id}'."
                )
            else:
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

            # 4. WIP Task Execution Progress & Locked Assignment Audit
            status_val = task.status.value if hasattr(task.status, "value") else str(task.status)
            if status_val in ("IN_PROGRESS", "STALLED"):
                prog = self.evidence.task_progress.get(task.task_id)
                if not prog or prog.remaining_duration_ticks is None:
                    coverage_gaps.append(
                        f"Missing execution progress and remaining duration evidence for active task '{task.task_id}'."
                    )
                else:
                    if prog.is_assignment_locked:
                        if prog.existing_bay_id and a.bay_id != prog.existing_bay_id:
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                                    constraint="C5",
                                    message=(
                                        f"Task '{task.task_id}' has locked existing bay '{prog.existing_bay_id}'; "
                                        f"cannot be reassigned to bay '{a.bay_id}'."
                                    ),
                                    entity_id=task.task_id,
                                )
                            )
                        if prog.existing_tech_id and a.tech_id != prog.existing_tech_id:
                            violations.append(
                                ConstraintViolation(
                                    code=ViolationCode.C1_SKILL_INELIGIBLE,
                                    constraint="C1",
                                    message=(
                                        f"Task '{task.task_id}' has locked existing technician '{prog.existing_tech_id}'; "
                                        f"cannot be reassigned to technician '{a.tech_id}'."
                                    ),
                                    entity_id=task.task_id,
                                )
                            )

        # 5. C6 Two-Week Rolling Flat-Rate Fairness Band Audit Across ALL Assigned Technicians
        tech_allocated_flat_rate_minutes: Dict[str, int] = defaultdict(int)
        for a in plan.assignments:
            task = self.tasks.get(a.task_id)
            if task:
                tech_allocated_flat_rate_minutes[a.tech_id] += task.flat_rate_minutes

        for tech_id in scheduled_tech_ids:
            fairness = self.evidence.technician_fairness.get(tech_id)
            if not fairness:
                coverage_gaps.append(
                    f"Technician '{tech_id}' has scheduled assignments but lacks required rolling two-week fairness evidence."
                )
            else:
                new_allocated_hours = Decimal(str(tech_allocated_flat_rate_minutes[tech_id])) / Decimal("60")
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
                                f"Technician '{tech_id}' total flat-rate hours ({total_hours:.2f}h) breaches "
                                f"15% peer fairness band [{min_allowed:.2f}h, {max_allowed:.2f}h]."
                            ),
                            entity_id=tech_id,
                        )
                    )

        # 6. Certification Status Evaluation
        if violations:
            status = CertificationStatus.INVALID_VIOLATIONS
            is_valid = False
        elif coverage_gaps:
            status = CertificationStatus.INCOMPLETE_EVIDENCE
            is_valid = False
        else:
            status = CertificationStatus.VALID_AND_CERTIFIED
            is_valid = True

        is_actionable = is_valid and (len(coverage_gaps) == 0) and (len(plan.assignments) > 0)

        return SupplementalAuditResult(
            is_valid=is_valid,
            certification_status=status,
            violations=[v.to_dict() for v in violations],
            coverage_gaps=coverage_gaps,
            is_actionable=is_actionable,
            details={
                "scheduled_ros_count": len(scheduled_ros),
                "authorized_ros_count": sum(1 for r in scheduled_ros if self.evidence.is_ro_authorized(r)),
                "scheduled_techs_count": len(scheduled_tech_ids),
                "covered_techs_fairness_count": sum(1 for t in scheduled_tech_ids if t in self.evidence.technician_fairness),
                "planned_movements_count": len(movements),
            },
        )
