"""Deterministic T1 Bitset Scheduler for ServiceYield AI Optimise Engine.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 3: Optimise)
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.3)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md (A3: $120/hr sold labor, nu = $2.00/min = $120/hr)
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md (Task 1.4)

Mathematical Principles:
1. Pure integer bitset occupancy representations over discrete 5-minute ticks [0, 288].
2. Immutable stable sort key: (-priority, promise_tick, sequence_order, duration_ticks, task_id).
3. Non-overlapping resource intervals: Technician, Bay, Lunch Break, Shift, Movement, Vehicle.
4. Hard gates: C1 eligibility, C2 parts, C3 precedence DAG, C4 exclusivity, C5 vehicle physical states/movement, C6 shifts/fairness, C7 customer authorizations.
5. Infallible fallback: sub-millisecond execution, zero external solver dependencies.
6. Dual verification: candidate plans must be certified by both L4 Sweep-Line Oracle and Supplemental Audit Oracle.
"""

from collections import defaultdict
from decimal import Decimal
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.optimise.config import OptimiseConfig
from app.optimise.evidence import WorkshopEvidenceBundle
from app.optimise.models import (
    ObjectiveMetrics,
    PlannedVehicleMovement,
    RepairOrderCompletionStatus,
    ScheduleResult,
    SchedulerTier,
    SolverStatus,
)
from app.optimise.supplemental_audit import SupplementalAuditOracle
from app.schemas.domain import (
    DealershipSnapshotSchema,
    TaskSchema,
    TaskStatus,
    VehiclePhysicalState,
)
from app.verifier.models import (
    CandidateSchedulePlan,
    ScheduledAssignment,
    VehicleBayOccupancy,
)
from app.verifier.sweep_oracle import SweepLineOracle


class BitsetOccupancyGrid:
    """Fast discrete-tick integer bitset occupancy grid over horizon [0, 288].
    
    Uses Python arbitrary-precision integers as bitmasks for true bitwise interval collision testing.
    mask(s, e) = ((1 << (e - s)) - 1) << s
    collision = (current_mask & interval_mask) != 0
    """

    def __init__(self, horizon_ticks: int = 288):
        self.horizon_ticks = horizon_ticks
        self._tech_busy: Dict[str, int] = defaultdict(int)
        self._bay_busy: Dict[str, int] = defaultdict(int)
        self._porter_busy: Dict[str, int] = defaultdict(int)

    @staticmethod
    def interval_mask(start_tick: int, end_tick: int) -> int:
        """Constructs an integer bitmask with bits [start_tick, end_tick) set to 1."""
        if start_tick >= end_tick or start_tick < 0:
            return 0
        return ((1 << (end_tick - start_tick)) - 1) << start_tick

    def mark_interval_busy(self, target: Any, start_tick: int, end_tick: int) -> int:
        """Marks interval [start_tick, end_tick) as busy in target bitmask or list."""
        if start_tick >= end_tick:
            return target if isinstance(target, int) else 0
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        mask = self.interval_mask(s, e)
        if isinstance(target, int):
            return target | mask
        elif isinstance(target, list):
            for t in range(s, e):
                target[t] = True
            return 0
        return 0

    def is_interval_free(self, mask_or_list: Any, start_tick: int, end_tick: int) -> bool:
        """True if every tick in [start_tick, end_tick) is unallocated (False / 0)."""
        if start_tick == end_tick:
            return True
        if start_tick > end_tick or start_tick < 0 or end_tick > self.horizon_ticks:
            return False
        if isinstance(mask_or_list, int):
            mask = self.interval_mask(start_tick, end_tick)
            return (mask_or_list & mask) == 0
        elif isinstance(mask_or_list, list):
            for t in range(start_tick, end_tick):
                if mask_or_list[t]:
                    return False
            return True
        return False

    def is_tech_free(self, tech_id: str, start_tick: int, end_tick: int) -> bool:
        if start_tick >= end_tick or start_tick < 0 or end_tick > self.horizon_ticks:
            return False
        mask = self.interval_mask(start_tick, end_tick)
        return (self._tech_busy[tech_id] & mask) == 0

    def is_bay_free(self, bay_id: str, start_tick: int, end_tick: int) -> bool:
        if start_tick >= end_tick or start_tick < 0 or end_tick > self.horizon_ticks:
            return False
        mask = self.interval_mask(start_tick, end_tick)
        return (self._bay_busy[bay_id] & mask) == 0

    def is_porter_free(self, porter_id: str, start_tick: int, end_tick: int) -> bool:
        if start_tick >= end_tick or start_tick < 0 or end_tick > self.horizon_ticks:
            return False
        mask = self.interval_mask(start_tick, end_tick)
        return (self._porter_busy[porter_id] & mask) == 0

    def allocate(self, tech_id: str, bay_id: str, start_tick: int, end_tick: int) -> None:
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        mask = self.interval_mask(s, e)
        self._tech_busy[tech_id] |= mask
        self._bay_busy[bay_id] |= mask

    def allocate_bay_only(self, bay_id: str, start_tick: int, end_tick: int) -> None:
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        mask = self.interval_mask(s, e)
        self._bay_busy[bay_id] |= mask

    def allocate_tech_only(self, tech_id: str, start_tick: int, end_tick: int) -> None:
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        mask = self.interval_mask(s, e)
        self._tech_busy[tech_id] |= mask

    def allocate_porter_only(self, porter_id: str, start_tick: int, end_tick: int) -> None:
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        mask = self.interval_mask(s, e)
        self._porter_busy[porter_id] |= mask

    # Public aliases
    mark_tech_busy = allocate_tech_only
    mark_bay_busy = allocate_bay_only


class T1BitsetScheduler:
    """Deterministic constructive earliest-fit bitset scheduler."""

    def __init__(self, config: Optional[OptimiseConfig] = None):
        self.config = config or OptimiseConfig()

    def schedule(
        self,
        snapshot: DealershipSnapshotSchema,
        plan_id: str = "PLAN-T1-DISPATCH",
        evidence: Optional[WorkshopEvidenceBundle] = None,
        blocked_bay_intervals: Optional[List[Tuple[str, int, int]]] = None,
        task_sort_key_fn: Optional[Any] = None,
    ) -> ScheduleResult:
        """Executes deterministic earliest-fit scheduling over the snapshot state."""
        start_time = time.perf_counter()
        ev = evidence or WorkshopEvidenceBundle(current_tick=snapshot.rooftop.operating_day_start_tick)
        unscheduled_reasons: Dict[str, str] = {}
        assignments: List[ScheduledAssignment] = []
        vehicle_occupancies: List[VehicleBayOccupancy] = []

        # 1. State Lookups
        bays_by_id = {b.bay_id: b for b in snapshot.bays}
        techs_by_id = {t.tech_id: t for t in snapshot.technicians}
        ros_by_id = {r.ro_id: r for r in snapshot.repair_orders}
        tasks_by_id = {t.task_id: t for t in snapshot.tasks}

        parts_by_task: Dict[str, List[Any]] = defaultdict(list)
        for p in snapshot.part_requirements:
            parts_by_task[p.task_id].append(p)

        # 2. Initialize Occupancy Grid
        grid = BitsetOccupancyGrid(horizon_ticks=self.config.horizon_ticks)

        # Pre-allocate technician shifts and lunch breaks into tech masks
        for tech in snapshot.technicians:
            if not tech.is_active:
                grid.allocate_tech_only(tech.tech_id, 0, self.config.horizon_ticks)
                continue

            if tech.shift_start_tick > 0:
                grid.allocate_tech_only(tech.tech_id, 0, tech.shift_start_tick)

            shift_cutoff = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else tech.shift_end_tick
            if shift_cutoff < self.config.horizon_ticks:
                grid.allocate_tech_only(tech.tech_id, shift_cutoff, self.config.horizon_ticks)

            lunch_end = tech.lunch_start_tick + tech.lunch_duration_ticks
            grid.allocate_tech_only(tech.tech_id, tech.lunch_start_tick, lunch_end)

        # Pre-allocate non-operational bays
        for bay in snapshot.bays:
            if not bay.is_operational:
                grid.allocate_bay_only(bay.bay_id, 0, self.config.horizon_ticks)

        # Pre-allocate externally blocked bay intervals
        if blocked_bay_intervals:
            for b_id, b_start, b_end in blocked_bay_intervals:
                if b_id in bays_by_id and b_end > b_start:
                    grid.allocate_bay_only(b_id, b_start, b_end)

        # Pre-allocate existing WIP active/stalled occupancy (Finding B1)
        for task in snapshot.tasks:
            status_val = task.status.value if hasattr(task.status, "value") else str(task.status)
            if status_val in ("IN_PROGRESS", "STALLED"):
                prog = ev.task_progress.get(task.task_id)
                if prog and prog.occupied_start_tick is not None:
                    occ_end = prog.occupied_end_tick if prog.occupied_end_tick is not None else ev.current_tick
                    if occ_end > prog.occupied_start_tick:
                        if prog.existing_tech_id:
                            grid.allocate_tech_only(prog.existing_tech_id, prog.occupied_start_tick, occ_end)
                        if prog.existing_bay_id:
                            grid.allocate_bay_only(prog.existing_bay_id, prog.occupied_start_tick, occ_end)

        # 3. Handle Vehicles IMMOBILIZED_ON_LIFT (C5)
        # Any vehicle trapped on a lift must retain its assigned bay exclusively
        immobilized_ros = {
            r.ro_id: r for r in snapshot.repair_orders
            if (r.physical_state.value if hasattr(r.physical_state, "value") else str(r.physical_state)) == "IMMOBILIZED_ON_LIFT"
        }
        immobilized_bay_reservations: Dict[str, str] = {}
        bay_to_imm_ro: Dict[str, str] = {}
        imm_missing_bays: Set[str] = set()

        for r_id, r in immobilized_ros.items():
            phys_ev = ev.get_vehicle_physical_evidence(r.vehicle_id, r_id)
            target_bay = (phys_ev.current_bay_id if phys_ev else None) or r.assigned_bay_id
            if not target_bay:
                imm_missing_bays.add(r_id)
            elif target_bay in bay_to_imm_ro:
                # Conflicting vehicle claiming the same bay!
                unscheduled_reasons[f"RO_{r_id}"] = f"CONFLICTING_IMMOBILIZED_BAY_OCCUPANCY_{target_bay}"
            else:
                immobilized_bay_reservations[r_id] = target_bay
                bay_to_imm_ro[target_bay] = r_id

        # 4. Filter and Sort Incomplete Tasks
        incomplete_tasks: List[TaskSchema] = []
        completed_task_ids: Set[str] = set()

        for t in snapshot.tasks:
            status_str = t.status.value if hasattr(t.status, "value") else str(t.status)
            if status_str == "COMPLETED":
                completed_task_ids.add(t.task_id)
            else:
                incomplete_tasks.append(t)

        # Precedence Cycle Detection (3-color DFS)
        predecessors: Dict[str, List[str]] = {t.task_id: t.predecessor_task_ids for t in incomplete_tasks}
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def detect_cycle(u: str) -> None:
            visiting.add(u)
            for p in predecessors.get(u, []):
                if p in predecessors:
                    if p in visiting:
                        raise ValueError(f"Precedence cycle detected involving task '{p}'")
                    if p not in visited:
                        detect_cycle(p)
            visiting.remove(u)
            visited.add(u)

        for t_id in predecessors:
            if t_id not in visited:
                detect_cycle(t_id)

        # Stable Deterministic Priority Ordering:
        def task_sort_key(task: TaskSchema) -> Tuple[int, int, int, int, str]:
            ro = ros_by_id.get(task.ro_id)
            priority = ro.priority_weight if ro else 1
            promise = ro.promise_tick if ro else 288
            return (-priority, promise, task.sequence_order, task.estimated_duration_ticks, task.task_id)

        if task_sort_key_fn is not None:
            incomplete_tasks.sort(key=lambda t: task_sort_key_fn(t, ros_by_id))
        else:
            incomplete_tasks.sort(key=task_sort_key)

        # 5. Iterative Earliest-Fit Dispatching with Transitive Precedence Closure
        task_completion_ticks: Dict[str, int] = {}
        scheduled_task_ids: Set[str] = set()
        unscheduled_task_ids: Set[str] = set()
        planned_movements: List[PlannedVehicleMovement] = []
        moved_vehicles: Set[str] = set()

        horizon_start = self.config.horizon_start_tick
        horizon_end = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else self.config.horizon_end_tick

        for task in incomplete_tasks:
            ro = ros_by_id.get(task.ro_id)
            if not ro:
                unscheduled_reasons[task.task_id] = "RO_NOT_FOUND"
                unscheduled_task_ids.add(task.task_id)
                continue

            # C7 Customer Estimate Authorization Gate (Zero Fabricated Approvals)
            if not ev.is_ro_authorized(task.ro_id):
                unscheduled_reasons[task.task_id] = f"UNAUTHORIZED_CUSTOMER_ESTIMATE_{task.ro_id}"
                unscheduled_task_ids.add(task.task_id)
                continue

            # C1 Parts Fitment Evidence Gate (Finding A2)
            phys_ev = ev.get_vehicle_physical_evidence(ro.vehicle_id, ro.ro_id)
            if phys_ev is None:
                unscheduled_reasons[task.task_id] = f"MISSING_VEHICLE_EVIDENCE_{ro.vehicle_id}"
                unscheduled_task_ids.add(task.task_id)
                continue

            if phys_ev.fitment_verified is None:
                unscheduled_reasons[task.task_id] = f"UNVERIFIED_PARTS_FITMENT_{ro.vehicle_id}"
                unscheduled_task_ids.add(task.task_id)
                continue
            elif phys_ev.fitment_verified is False:
                unscheduled_reasons[task.task_id] = f"REJECTED_PARTS_FITMENT_{ro.vehicle_id}"
                unscheduled_task_ids.add(task.task_id)
                continue

            # C1 Vehicle Weight Evidence Gate (Finding A3)
            if phys_ev.vehicle_weight_lbs is None:
                unscheduled_reasons[task.task_id] = f"MISSING_VEHICLE_WEIGHT_EVIDENCE_{ro.vehicle_id}"
                unscheduled_task_ids.add(task.task_id)
                continue
            vehicle_weight = phys_ev.vehicle_weight_lbs

            # C5 Vehicle Physical State & Holding Staging Gate
            state_val = (
                phys_ev.physical_state.value if hasattr(phys_ev.physical_state, "value")
                else (ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state))
            )
            if state_val == "UNKNOWN":
                unscheduled_reasons[task.task_id] = f"UNKNOWN_VEHICLE_STATE_{ro.ro_id}"
                unscheduled_task_ids.add(task.task_id)
                continue

            # Immobilized vehicle check (Primary Task C)
            if state_val == "IMMOBILIZED_ON_LIFT":
                if ro.ro_id in imm_missing_bays:
                    unscheduled_reasons[task.task_id] = f"IMMOBILIZED_VEHICLE_MISSING_ASSIGNED_BAY_{ro.ro_id}"
                    unscheduled_task_ids.add(task.task_id)
                    continue

            # Task Execution Progress and Remaining Duration Evidence (Finding B1)
            status_val = task.status.value if hasattr(task.status, "value") else str(task.status)
            if status_val in ("IN_PROGRESS", "STALLED"):
                prog = ev.task_progress.get(task.task_id)
                if not prog:
                    unscheduled_reasons[task.task_id] = f"MISSING_EXECUTION_PROGRESS_{task.task_id}"
                    unscheduled_task_ids.add(task.task_id)
                    continue
                if prog.remaining_duration_ticks is None or prog.remaining_duration_ticks <= 0:
                    unscheduled_reasons[task.task_id] = f"MISSING_EXECUTION_PROGRESS_REMAINING_DURATION_{task.task_id}"
                    unscheduled_task_ids.add(task.task_id)
                    continue
                if prog.requires_existing_assignment and (not prog.existing_bay_id or not prog.existing_tech_id):
                    unscheduled_reasons[task.task_id] = f"MISSING_EXISTING_ASSIGNMENT_EVIDENCE_{task.task_id}"
                    unscheduled_task_ids.add(task.task_id)
                    continue
                duration = prog.remaining_duration_ticks
            else:
                effective_duration = ev.get_effective_remaining_duration(
                    task.task_id, task.status, task.estimated_duration_ticks
                )
                if effective_duration is None:
                    unscheduled_reasons[task.task_id] = f"MISSING_EXECUTION_PROGRESS_{task.task_id}"
                    unscheduled_task_ids.add(task.task_id)
                    continue
                if effective_duration <= 0:
                    completed_task_ids.add(task.task_id)
                    continue
                duration = effective_duration

            # C3 Precedence Closure Gate
            pred_blocked = False
            earliest_pred_tick = horizon_start
            for pred_id in task.predecessor_task_ids:
                if pred_id in completed_task_ids:
                    continue
                elif pred_id in unscheduled_task_ids:
                    unscheduled_reasons[task.task_id] = f"PREDECESSOR_UNSCHEDULED_{pred_id}"
                    pred_blocked = True
                    break
                elif pred_id in task_completion_ticks:
                    earliest_pred_tick = max(earliest_pred_tick, task_completion_ticks[pred_id])
                else:
                    unscheduled_reasons[task.task_id] = f"PREDECESSOR_UNSCHEDULED_{pred_id}"
                    pred_blocked = True
                    break

            if pred_blocked:
                unscheduled_task_ids.add(task.task_id)
                continue

            # C2 Part Availability Gate
            task_parts = parts_by_task.get(task.task_id, [])
            earliest_part_tick = horizon_start
            part_blocked = False

            for part in task_parts:
                if part.usable_ready_tick is None:
                    unscheduled_reasons[task.task_id] = f"PART_NOT_READY_NO_ETA_{part.part_req_id}"
                    part_blocked = True
                    break
                earliest_part_tick = max(earliest_part_tick, part.usable_ready_tick)

            if part_blocked:
                unscheduled_task_ids.add(task.task_id)
                continue

            is_holding = (phys_ev.is_in_holding if phys_ev else (state_val == "IN_HOLDING")) and (ro.vehicle_id not in moved_vehicles)
            if is_holding and not ev.available_porter_tech_ids:
                unscheduled_reasons[task.task_id] = f"NO_PORTER_OR_TECH_AVAILABLE_FOR_MOVE_{ro.ro_id}"
                unscheduled_task_ids.add(task.task_id)
                continue

            earliest_move_tick = (ev.current_tick + 2) if is_holding else horizon_start
            earliest_possible_start = max(ev.current_tick, horizon_start, earliest_part_tick, earliest_pred_tick, earliest_move_tick)

            # WIP Locked Assignments (Finding B1)
            prog = ev.task_progress.get(task.task_id)
            locked_bay_id = prog.existing_bay_id if (prog and prog.is_assignment_locked and prog.existing_bay_id) else None
            locked_tech_id = prog.existing_tech_id if (prog and prog.is_assignment_locked and prog.existing_tech_id) else None

            # C1 Skills Match
            if locked_tech_id:
                eligible_techs = [
                    t for t in snapshot.technicians
                    if t.tech_id == locked_tech_id and t.is_active and task.required_skill in t.skill_certifications
                ]
            else:
                eligible_techs = [
                    t for t in snapshot.technicians
                    if t.is_active and task.required_skill in t.skill_certifications
                ]

            if not eligible_techs:
                unscheduled_reasons[task.task_id] = f"NO_ELIGIBLE_TECHNICIAN_SKILL_{task.required_skill}"
                unscheduled_task_ids.add(task.task_id)
                continue

            # C1 Bay Compatibility & Weight Rating Gate
            target_bay_id = immobilized_bay_reservations.get(ro.ro_id)
            if target_bay_id:
                assigned_bay = bays_by_id.get(target_bay_id)
                if (
                    not assigned_bay
                    or not assigned_bay.is_operational
                    or assigned_bay.bay_type != task.required_bay_type
                    or assigned_bay.lifting_capacity_lbs < vehicle_weight
                ):
                    unscheduled_reasons[task.task_id] = f"IMMOBILIZED_BAY_INCOMPATIBLE_{target_bay_id}"
                    unscheduled_task_ids.add(task.task_id)
                    continue
                compatible_bays = [assigned_bay]
            elif locked_bay_id:
                assigned_bay = bays_by_id.get(locked_bay_id)
                if (
                    not assigned_bay
                    or not assigned_bay.is_operational
                    or assigned_bay.bay_type != task.required_bay_type
                    or assigned_bay.lifting_capacity_lbs < vehicle_weight
                ):
                    unscheduled_reasons[task.task_id] = f"LOCKED_BAY_INCOMPATIBLE_{locked_bay_id}"
                    unscheduled_task_ids.add(task.task_id)
                    continue
                compatible_bays = [assigned_bay]
            else:
                compatible_bays = [
                    b for b in snapshot.bays
                    if b.is_operational
                    and b.bay_type == task.required_bay_type
                    and b.bay_id not in immobilized_bay_reservations.values()
                    and b.lifting_capacity_lbs >= vehicle_weight
                ]

            if not compatible_bays:
                unscheduled_reasons[task.task_id] = f"NO_COMPATIBLE_OPERATIONAL_BAY_{task.required_bay_type}"
                unscheduled_task_ids.add(task.task_id)
                continue

            eligible_techs.sort(key=lambda t: t.tech_id)
            compatible_bays.sort(key=lambda b: b.bay_id)

            # Earliest-Fit Search
            scheduled = False
            for t_start in range(earliest_possible_start, horizon_end - duration + 1):
                t_end = t_start + duration

                # C5 Movement Resource Availability Check
                allocated_porter = None
                if is_holding:
                    m_start = t_start - 2
                    m_end = t_start
                    for p_id in sorted(ev.available_porter_tech_ids):
                        if p_id in techs_by_id:
                            if grid.is_tech_free(p_id, m_start, m_end):
                                allocated_porter = p_id
                                break
                        else:
                            if grid.is_porter_free(p_id, m_start, m_end):
                                allocated_porter = p_id
                                break
                    if not allocated_porter:
                        continue  # Cannot move vehicle at this time

                for bay in compatible_bays:
                    if not grid.is_bay_free(bay.bay_id, t_start, t_end):
                        continue
                    for tech in eligible_techs:
                        if not grid.is_tech_free(tech.tech_id, t_start, t_end):
                            continue

                        # Feasible slot found! Allocate atomically
                        grid.allocate(tech.tech_id, bay.bay_id, t_start, t_end)
                        if is_holding and allocated_porter:
                            if allocated_porter in techs_by_id:
                                grid.allocate_tech_only(allocated_porter, t_start - 2, t_start)
                            else:
                                grid.allocate_porter_only(allocated_porter, t_start - 2, t_start)
                            planned_movements.append(
                                PlannedVehicleMovement(
                                    vehicle_id=ro.vehicle_id,
                                    ro_id=ro.ro_id,
                                    origin_location="HOLDING_LOT",
                                    target_bay_id=bay.bay_id,
                                    start_tick=t_start - 2,
                                    end_tick=t_start,
                                    assigned_resource_id=allocated_porter,
                                    resource_type="TECHNICIAN" if allocated_porter in techs_by_id else "PORTER",
                                    resource_availability="AVAILABLE",
                                    movement_status="PLANNED",
                                    related_task_id=task.task_id,
                                )
                            )
                            moved_vehicles.add(ro.vehicle_id)

                        assignments.append(
                            ScheduledAssignment(
                                task_id=task.task_id,
                                ro_id=task.ro_id,
                                tech_id=tech.tech_id,
                                bay_id=bay.bay_id,
                                start_tick=t_start,
                                end_tick=t_end,
                            )
                        )
                        task_completion_ticks[task.task_id] = t_end
                        scheduled_task_ids.add(task.task_id)
                        scheduled = True
                        break
                    if scheduled:
                        break
                if scheduled:
                    break

            if not scheduled:
                unscheduled_reasons[task.task_id] = "NO_FEASIBLE_INTERVAL_WITHIN_HORIZON"
                unscheduled_task_ids.add(task.task_id)

        # 6. Reconstruct Vehicle Occupancy for Immobilized Vehicles (Primary Task C)
        for imm_ro_id, imm_ro in immobilized_ros.items():
            assigned_bay = immobilized_bay_reservations.get(imm_ro_id)
            if assigned_bay:
                phys_ev = ev.get_vehicle_physical_evidence(imm_ro.vehicle_id, imm_ro_id)
                occ_start = phys_ev.occupancy_start_tick if (phys_ev and phys_ev.occupancy_start_tick is not None) else ev.current_tick
                imm_assignments = [a for a in assignments if a.ro_id == imm_ro_id]
                if imm_assignments:
                    first_start = min(a.start_tick for a in imm_assignments)
                    if first_start > occ_start:
                        vehicle_occupancies.append(
                            VehicleBayOccupancy(
                                vehicle_id=imm_ro.vehicle_id,
                                ro_id=imm_ro.ro_id,
                                bay_id=assigned_bay,
                                start_tick=occ_start,
                                end_tick=first_start,
                            )
                        )
                else:
                    vehicle_occupancies.append(
                        VehicleBayOccupancy(
                            vehicle_id=imm_ro.vehicle_id,
                            ro_id=imm_ro.ro_id,
                            bay_id=assigned_bay,
                            start_tick=occ_start,
                            end_tick=horizon_end,
                        )
                    )

        # 7. Calculate Objective Metrics & Incomplete RO Analysis (Finding F1 & F2)
        total_labor_ticks = sum(a.end_tick - a.start_tick for a in assignments)
        gross_contrib = (Decimal(str(total_labor_ticks)) * self.config.labor_contribution_per_hour_usd) / Decimal("12")

        # RO Completion Lifecycle Analysis
        ro_completion_statuses: Dict[str, str] = {}
        uncompleted_ros_count = 0
        scheduled_ro_ids = {a.ro_id for a in assignments}
        weighted_lateness_ticks = 0

        for ro in snapshot.repair_orders:
            ro_tasks = [t for t in snapshot.tasks if t.ro_id == ro.ro_id]
            scheduled_t_ids = {a.task_id for a in assignments if a.ro_id == ro.ro_id}
            completed_t_ids = {t.task_id for t in ro_tasks if (t.status.value if hasattr(t.status, "value") else str(t.status)) == "COMPLETED"}

            if all(t.task_id in completed_t_ids for t in ro_tasks):
                ro_completion_statuses[ro.ro_id] = RepairOrderCompletionStatus.COMPLETED.value
            elif set(t.task_id for t in ro_tasks).issubset(scheduled_t_ids | completed_t_ids):
                ro_completion_statuses[ro.ro_id] = RepairOrderCompletionStatus.FULLY_SCHEDULED.value
                ro_assignments = [a for a in assignments if a.ro_id == ro.ro_id]
                completion_tick = max(a.end_tick for a in ro_assignments)
                lateness_ticks = max(0, completion_tick - ro.promise_tick)
                weighted_lateness_ticks += ro.priority_weight * lateness_ticks
            else:
                uncompleted_ros_count += 1
                if any(a.task_id in scheduled_t_ids for a in ro_tasks):
                    ro_completion_statuses[ro.ro_id] = RepairOrderCompletionStatus.PARTIALLY_SCHEDULED.value
                elif any("PART_NOT_READY" in unscheduled_reasons.get(t.task_id, "") for t in ro_tasks):
                    ro_completion_statuses[ro.ro_id] = RepairOrderCompletionStatus.BLOCKED_BY_PARTS.value
                elif any("UNAUTHORIZED" in unscheduled_reasons.get(t.task_id, "") or "MISSING_" in unscheduled_reasons.get(t.task_id, "") for t in ro_tasks):
                    ro_completion_statuses[ro.ro_id] = RepairOrderCompletionStatus.BLOCKED_BY_EVIDENCE.value
                else:
                    ro_completion_statuses[ro.ro_id] = RepairOrderCompletionStatus.UNSCHEDULABLE_IN_HORIZON.value

        # Financial objective calculation using exact cents
        gross_cents = total_labor_ticks * 1000
        late_cents = weighted_lateness_ticks * 250
        gross_contrib = Decimal(str(gross_cents)) / Decimal("100")
        lateness_penalty = Decimal(str(late_cents)) / Decimal("100")

        # Calculate Avoidable Idle Bay Blocked Ticks (Diagnostic metric)
        bay_blocked_ticks = sum(occ.end_tick - occ.start_tick for occ in vehicle_occupancies)
        bay_blocked_penalty = Decimal("0.00")
        net_obj = gross_contrib - lateness_penalty

        metrics = ObjectiveMetrics(
            gross_contribution_usd=gross_contrib.quantize(Decimal("0.01")),
            sourcing_cost_usd=Decimal("0.00"),
            weighted_lateness_ticks=weighted_lateness_ticks,
            lateness_penalty_usd=lateness_penalty.quantize(Decimal("0.01")),
            bay_blocked_ticks=bay_blocked_ticks,
            bay_blocked_penalty_usd=Decimal("0.00"),
            schedule_churn_score=None,
            schedule_churn_penalty_usd=None,
            churn_status="NOT_APPLICABLE",
            net_objective_usd=net_obj.quantize(Decimal("0.01")),
            objective_completeness="PARTIAL_CONFIGURED",
            configured_terms=["gross_contribution", "lateness_penalty"],
            unconfigured_terms=["sourcing_cost", "bay_blocked_penalty", "schedule_churn_penalty"],
            ro_completion_statuses=ro_completion_statuses,
            uncompleted_ros_count=uncompleted_ros_count,
        )

        # 8. Candidate Schedule Plan Assembly
        verified_authorizations = {r_id: True for r_id in scheduled_ro_ids if ev.is_ro_authorized(r_id)}
        verified_freight = {
            o_id: True for o_id, appr in ev.manager_freight_approvals.items() if appr.is_approved
        }

        candidate_plan = CandidateSchedulePlan(
            plan_id=plan_id,
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            assignments=assignments,
            vehicle_occupancies=vehicle_occupancies,
            customer_authorizations=verified_authorizations,
            manager_freight_approvals=verified_freight,
            allow_emergency_overtime=self.config.allow_emergency_overtime,
        )

        # 9. Dual Independent Verification (Primary Task E)
        oracle = SweepLineOracle(snapshot)
        verification_result = oracle.verify_plan(candidate_plan)

        supp_oracle = SupplementalAuditOracle(snapshot, ev)
        supp_result = supp_oracle.audit_plan(candidate_plan, planned_movements=planned_movements)

        has_assignments = len(assignments) > 0
        has_incomplete = any((t.status.value if hasattr(t.status, "value") else str(t.status)) != "COMPLETED" for t in snapshot.tasks)

        is_verified = verification_result.is_valid and (has_assignments or not has_incomplete)
        is_fully_certified = is_verified and supp_result.is_valid
        is_actionable = has_assignments and is_fully_certified and (len(supp_result.coverage_gaps) == 0) and getattr(supp_result, "is_actionable", True)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if has_assignments:
            solver_status = SolverStatus.FEASIBLE if is_verified else SolverStatus.UNKNOWN
        else:
            solver_status = SolverStatus.OPTIMAL if (not has_incomplete and is_verified) else SolverStatus.UNKNOWN

        return ScheduleResult(
            plan_id=plan_id,
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            solver_tier=SchedulerTier.T1_HEURISTIC,
            solver_status=solver_status,
            runtime_ms=round(elapsed_ms, 3),
            objective_value_usd=net_obj.quantize(Decimal("0.01")),
            best_bound_usd=None,
            optimality_gap=None,
            plan=candidate_plan,
            planned_movements=planned_movements,
            metrics=metrics,
            unscheduled_tasks=unscheduled_reasons,
            verification_result=verification_result,
            is_verified=is_verified,
            supplemental_audit_result=supp_result.model_dump(),
            is_fully_certified=is_fully_certified,
            is_actionable=is_actionable,
            evidence_coverage_gaps=supp_result.coverage_gaps,
            ro_completion_statuses=ro_completion_statuses,
            degradation_reason=None if is_fully_certified else f"T1 plan uncertified: L4 valid={is_verified}, Supp valid={supp_result.is_valid}",
        )
