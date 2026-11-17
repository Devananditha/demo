"""L4 Independent Verifier — Sweep-Line Interval Validation Oracle.

Authoritative Reference:
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- Technical Report Sections 5.1, 5.2, 8.5

The L4 Verifier is an independent, pure-Python O(N log N) sweep-line interval
validation oracle that certifies candidate workshop schedules before commit.
It shares ZERO heuristic or solver code with the CP-SAT engine.
"""

from collections import defaultdict
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.constraints.rules import (
    ConstraintViolation,
    ViolationCode,
    check_c1_bay_compatibility,
    check_c1_technician_skill,
    check_c2_part_ready,
    check_c3_precedence,
    check_c5_vehicle_movement,
    check_c6_technician_break,
    check_c6_technician_shift,
    check_c7_customer_authorization,
    check_c7_freight_threshold,
    check_c7_snapshot_concurrency,
)
from app.schemas.domain import DealershipSnapshotSchema
from app.verifier.models import CandidateSchedulePlan, ScheduledAssignment, VerificationResult


# Event ordering: END events must process BEFORE START events at the same tick
# to permit seamless contiguous task transitions without false overlap rejections.
EVENT_END: int = 0
EVENT_START: int = 1


class SweepLineOracle:
    """Independent O(N log N) sweep-line verification engine."""

    def __init__(self, snapshot: DealershipSnapshotSchema):
        self.snapshot = snapshot
        
        # Indexed lookups for O(1) attribute access
        self.bays: Dict[str, Any] = {b.bay_id: b for b in snapshot.bays}
        self.technicians: Dict[str, Any] = {t.tech_id: t for t in snapshot.technicians}
        self.repair_orders: Dict[str, Any] = {r.ro_id: r for r in snapshot.repair_orders}
        self.tasks: Dict[str, Any] = {t.task_id: t for t in snapshot.tasks}
        self.part_requirements: Dict[str, Any] = {p.part_req_id: p for p in snapshot.part_requirements}
        self.parts_by_task: Dict[str, List[Any]] = defaultdict(list)
        for p in snapshot.part_requirements:
            self.parts_by_task[p.task_id].append(p)
            
        self.offers_by_part: Dict[str, List[Any]] = defaultdict(list)
        for o in snapshot.supplier_offers:
            self.offers_by_part[o.part_req_id].append(o)

    def verify_plan(self, plan: CandidateSchedulePlan) -> VerificationResult:
        """Audits a candidate schedule plan against all C1–C7 hard constraints.
        
        Returns:
            VerificationResult with status PASS (if zero violations) or FAIL.
        """
        start_time = time.perf_counter()
        violations: List[ConstraintViolation] = []

        # ====================================================================
        # 1. C7 AUDIT: OPTIMISTIC CONCURRENCY CONTROL (OCC)
        # ====================================================================
        expected_hash = self.snapshot.snapshot_hash or ""
        valid_occ, code, msg = check_c7_snapshot_concurrency(plan.snapshot_hash, expected_hash)
        if not valid_occ:
            violations.append(
                ConstraintViolation(
                    code=code or ViolationCode.C7_STALE_SNAPSHOT_HASH,
                    constraint="C7",
                    message=msg,
                    entity_id=plan.plan_id,
                    context={"plan_hash": plan.snapshot_hash, "current_hash": expected_hash},
                )
            )

        # ====================================================================
        # 2. C7 AUDIT: CUSTOMER AUTHORIZATIONS & FREIGHT POLICY
        # ====================================================================
        # Customer authorization audit
        for ro_id in {a.ro_id for a in plan.assignments}:
            is_authorized = plan.customer_authorizations.get(ro_id, True)  # defaults authorized if not specified
            auth_ok, code, msg = check_c7_customer_authorization(is_authorized)
            if not auth_ok:
                violations.append(
                    ConstraintViolation(
                        code=code or ViolationCode.C7_UNAUTHORIZED_REPAIR,
                        constraint="C7",
                        message=f"RO '{ro_id}': {msg}",
                        entity_id=ro_id,
                        context={"ro_id": ro_id},
                    )
                )

        # Expedited freight surcharge policy audit
        for offer in self.snapshot.supplier_offers:
            is_approved = plan.manager_freight_approvals.get(offer.offer_id, False)
            freight_ok, code, msg = check_c7_freight_threshold(
                freight_surcharge_usd=offer.freight_surcharge_usd,
                threshold_usd=offer.freight_surcharge_usd if offer.freight_surcharge_usd <= 50 else 50,
                is_manager_approved=is_approved,
            )
            if not freight_ok:
                violations.append(
                    ConstraintViolation(
                        code=code or ViolationCode.C7_FREIGHT_LIMIT_EXCEEDED,
                        constraint="C7",
                        message=f"Offer '{offer.offer_id}': {msg}",
                        entity_id=offer.offer_id,
                        context={"offer_id": offer.offer_id, "freight": str(offer.freight_surcharge_usd)},
                    )
                )

        # ====================================================================
        # 3. INDIVIDUAL ASSIGNMENT AUDITS (C1, C2, C5, C6)
        # ====================================================================
        # Map task completion ticks for C3 precedence verification
        task_end_ticks: Dict[str, int] = {}
        task_start_ticks: Dict[str, int] = {}

        for assignment in plan.assignments:
            task_id = assignment.task_id
            task = self.tasks.get(task_id)
            tech = self.technicians.get(assignment.tech_id)
            bay = self.bays.get(assignment.bay_id)
            ro = self.repair_orders.get(assignment.ro_id)

            task_start_ticks[task_id] = assignment.start_tick
            task_end_ticks[task_id] = assignment.end_tick

            # Basic entity existence
            if not task:
                violations.append(
                    ConstraintViolation(
                        code=ViolationCode.C1_SKILL_INELIGIBLE,
                        constraint="C1",
                        message=f"Assignment references non-existent task '{task_id}'.",
                        entity_id=task_id,
                    )
                )
                continue

            # C1: Technician Skill Match
            if tech:
                skill_ok, code, msg = check_c1_technician_skill(tech.skill_certifications, task.required_skill)
                if not skill_ok:
                    violations.append(
                        ConstraintViolation(
                            code=code or ViolationCode.C1_SKILL_INELIGIBLE,
                            constraint="C1",
                            message=f"Task '{task_id}' assigned to Tech '{tech.tech_id}': {msg}",
                            entity_id=tech.tech_id,
                            tick=assignment.start_tick,
                            context={"required_skill": task.required_skill, "tech_skills": tech.skill_certifications},
                        )
                    )

            # C1: Bay Capability & Operability
            if bay:
                bay_ok, code, msg = check_c1_bay_compatibility(
                    bay_type=bay.bay_type,
                    required_bay_type=task.required_bay_type,
                    is_operational=bay.is_operational,
                    lifting_capacity_lbs=bay.lifting_capacity_lbs,
                )
                if not bay_ok:
                    violations.append(
                        ConstraintViolation(
                            code=code or ViolationCode.C1_BAY_TYPE_INELIGIBLE,
                            constraint="C1",
                            message=f"Task '{task_id}' assigned to Bay '{bay.bay_id}': {msg}",
                            entity_id=bay.bay_id,
                            tick=assignment.start_tick,
                            context={"required_bay_type": task.required_bay_type, "bay_type": bay.bay_type},
                        )
                    )

            # C2: Part Availability & Usable-Ready Timing
            required_parts = self.parts_by_task.get(task_id, [])
            for part in required_parts:
                part_ok, code, msg = check_c2_part_ready(assignment.start_tick, part.usable_ready_tick)
                if not part_ok:
                    violations.append(
                        ConstraintViolation(
                            code=code or ViolationCode.C2_PART_NOT_READY,
                            constraint="C2",
                            message=f"Task '{task_id}' requires Part '{part.part_req_id}': {msg}",
                            entity_id=part.part_req_id,
                            tick=assignment.start_tick,
                            context={"usable_ready_tick": part.usable_ready_tick, "task_start_tick": assignment.start_tick},
                        )
                    )

            # C5: Vehicle Movement & Physical State Machine
            if ro:
                move_ok, code, msg = check_c5_vehicle_movement(
                    physical_state=ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state),
                    currently_assigned_bay_id=ro.assigned_bay_id,
                    target_bay_id=assignment.bay_id,
                )
                if not move_ok:
                    violations.append(
                        ConstraintViolation(
                            code=code or ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                            constraint="C5",
                            message=f"Vehicle for RO '{ro.ro_id}': {msg}",
                            entity_id=ro.ro_id,
                            tick=assignment.start_tick,
                            context={"assigned_bay": ro.assigned_bay_id, "target_bay": assignment.bay_id},
                        )
                    )

            # C6: Technician Shift Boundary & Meal Break
            if tech:
                shift_ok, code, msg = check_c6_technician_shift(
                    task_start_tick=assignment.start_tick,
                    task_end_tick=assignment.end_tick,
                    shift_start_tick=tech.shift_start_tick,
                    shift_end_tick=tech.shift_end_tick,
                    allow_overtime=plan.allow_emergency_overtime,
                    overtime_cutoff_tick=self.snapshot.rooftop.overtime_cutoff_tick,
                )
                if not shift_ok:
                    violations.append(
                        ConstraintViolation(
                            code=code or ViolationCode.C6_OUTSIDE_SHIFT,
                            constraint="C6",
                            message=f"Task '{task_id}' for Tech '{tech.tech_id}': {msg}",
                            entity_id=tech.tech_id,
                            tick=assignment.start_tick,
                            context={"shift_start": tech.shift_start_tick, "shift_end": tech.shift_end_tick},
                        )
                    )

                break_ok, code, msg = check_c6_technician_break(
                    task_start_tick=assignment.start_tick,
                    task_end_tick=assignment.end_tick,
                    lunch_start_tick=tech.lunch_start_tick,
                    lunch_duration_ticks=tech.lunch_duration_ticks,
                )
                if not break_ok:
                    violations.append(
                        ConstraintViolation(
                            code=code or ViolationCode.C6_BREAK_WINDOW_BREACH,
                            constraint="C6",
                            message=f"Task '{task_id}' for Tech '{tech.tech_id}': {msg}",
                            entity_id=tech.tech_id,
                            tick=assignment.start_tick,
                            context={"lunch_start": tech.lunch_start_tick, "lunch_duration": tech.lunch_duration_ticks},
                        )
                    )

        # ====================================================================
        # 4. C3 AUDIT: OPERATION PRECEDENCE (Task DAG)
        # ====================================================================
        for assignment in plan.assignments:
            task = self.tasks.get(assignment.task_id)
            if not task:
                continue
            for pred_id in task.predecessor_task_ids:
                if pred_id in task_end_ticks:
                    pred_end = task_end_ticks[pred_id]
                    prec_ok, code, msg = check_c3_precedence(pred_end, assignment.start_tick)
                    if not prec_ok:
                        violations.append(
                            ConstraintViolation(
                                code=code or ViolationCode.C3_PRECEDENCE_VIOLATION,
                                constraint="C3",
                                message=f"Task '{assignment.task_id}' has predecessor '{pred_id}': {msg}",
                                entity_id=assignment.task_id,
                                tick=assignment.start_tick,
                                context={"pred_id": pred_id, "pred_end": pred_end, "task_start": assignment.start_tick},
                            )
                        )

        # ====================================================================
        # 5. C4 AUDIT: SWEEP-LINE RESOURCE EXCLUSIVITY (Bays & Technicians)
        # ====================================================================
        # Point events format: (tick, event_order, resource_type, resource_id, item_id)
        events: List[Tuple[int, int, str, str, str]] = []

        for assignment in plan.assignments:
            # Bay events
            events.append((assignment.start_tick, EVENT_START, "bay", assignment.bay_id, assignment.task_id))
            events.append((assignment.end_tick, EVENT_END, "bay", assignment.bay_id, assignment.task_id))
            # Tech events
            events.append((assignment.start_tick, EVENT_START, "tech", assignment.tech_id, assignment.task_id))
            events.append((assignment.end_tick, EVENT_END, "tech", assignment.tech_id, assignment.task_id))

        # Vehicle bay occupancy events (e.g. stalled immobilized vehicle occupying bay)
        for occ in plan.vehicle_occupancies:
            events.append((occ.start_tick, EVENT_START, "bay_occ", occ.bay_id, f"OCC-{occ.vehicle_id}"))
            events.append((occ.end_tick, EVENT_END, "bay_occ", occ.bay_id, f"OCC-{occ.vehicle_id}"))

        # Sort events: primary key = tick ascending; secondary key = event_order ascending (END before START)
        events.sort(key=lambda e: (e[0], e[1]))

        # Active sets: resource_id -> Set of active task/item IDs
        active_bay_tasks: Dict[str, Set[str]] = defaultdict(set)
        active_tech_tasks: Dict[str, Set[str]] = defaultdict(set)
        active_bay_occupancies: Dict[str, Set[str]] = defaultdict(set)

        for tick, event_type, res_type, res_id, item_id in events:
            if res_type == "bay":
                if event_type == EVENT_START:
                    # Check if bay already occupied by another task or vehicle
                    if len(active_bay_tasks[res_id]) > 0 or len(active_bay_occupancies[res_id]) > 0:
                        conflicting = list(active_bay_tasks[res_id]) + list(active_bay_occupancies[res_id])
                        violations.append(
                            ConstraintViolation(
                                code=ViolationCode.C4_BAY_DOUBLE_BOOKED,
                                constraint="C4",
                                message=f"Bay '{res_id}' double-booked at tick {tick} by '{item_id}'. Active: {conflicting}.",
                                entity_id=res_id,
                                tick=tick,
                                context={"conflicting_items": conflicting, "item_id": item_id},
                            )
                        )
                    active_bay_tasks[res_id].add(item_id)
                else:  # EVENT_END
                    active_bay_tasks[res_id].discard(item_id)

            elif res_type == "tech":
                if event_type == EVENT_START:
                    # Check if technician already working on another task
                    if len(active_tech_tasks[res_id]) > 0:
                        conflicting = list(active_tech_tasks[res_id])
                        violations.append(
                            ConstraintViolation(
                                code=ViolationCode.C4_TECH_DOUBLE_BOOKED,
                                constraint="C4",
                                message=f"Technician '{res_id}' double-booked at tick {tick} by '{item_id}'. Active: {conflicting}.",
                                entity_id=res_id,
                                tick=tick,
                                context={"conflicting_tasks": conflicting, "task_id": item_id},
                            )
                        )
                    active_tech_tasks[res_id].add(item_id)
                else:  # EVENT_END
                    active_tech_tasks[res_id].discard(item_id)

            elif res_type == "bay_occ":
                if event_type == EVENT_START:
                    if len(active_bay_tasks[res_id]) > 0 or len(active_bay_occupancies[res_id]) > 0:
                        conflicting = list(active_bay_tasks[res_id]) + list(active_bay_occupancies[res_id])
                        violations.append(
                            ConstraintViolation(
                                code=ViolationCode.C4_BAY_DOUBLE_BOOKED,
                                constraint="C4",
                                message=f"Bay '{res_id}' double-booked at tick {tick} by vehicle occupancy '{item_id}'. Active: {conflicting}.",
                                entity_id=res_id,
                                tick=tick,
                                context={"conflicting_items": conflicting, "occupancy_id": item_id},
                            )
                        )
                    active_bay_occupancies[res_id].add(item_id)
                else:  # EVENT_END
                    active_bay_occupancies[res_id].discard(item_id)

        # ====================================================================
        # FINAL CERTIFICATION RESULT
        # ====================================================================
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        is_valid = len(violations) == 0

        return VerificationResult(
            plan_id=plan.plan_id,
            snapshot_hash=plan.snapshot_hash,
            is_valid=is_valid,
            violations=violations,
            execution_time_ms=elapsed_ms,
        )
