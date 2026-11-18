"""T1 Deterministic Constructive Earliest-Fit Bitset Dispatch Scheduler.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 3: Module 2 Optimise)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md (A3: $120/hr sold labor)
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md (Task 1.4)

Design Guarantees:
1. True integer bitset masks for constant-time O(1) interval collision testing.
2. Inviolable hard constraints C1–C7 (eligibility, parts release, precedence, exclusivity, shifts, breaks).
3. Zero manufactured evidence: strict customer authorization gate (C7) and execution progress requirements.
4. Transitive precedence closure: a successor is never scheduled if its incomplete predecessor failed to schedule.
5. Vehicle physical state gates: immobilized lifts locked; holding vehicles require movement delays (Delta t_move = 2).
6. Dual verification: Certified PASS by independent L4 Sweep-Line Oracle AND Supplemental Audit Oracle.
"""

from collections import defaultdict
from decimal import Decimal
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.optimise.config import OptimiseConfig
from app.optimise.evidence import WorkshopEvidenceBundle
from app.optimise.models import (
    ObjectiveMetrics,
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
    
    Uses Python arbitrary-precision integers as bitmasks for true O(1) interval collision testing.
    mask(s, e) = ((1 << (e - s)) - 1) << s
    collision = (current_mask & interval_mask) != 0
    """

    def __init__(self, horizon_ticks: int = 288):
        self.horizon_ticks = horizon_ticks
        self._tech_busy: Dict[str, int] = defaultdict(int)
        self._bay_busy: Dict[str, int] = defaultdict(int)

    @staticmethod
    def interval_mask(start_tick: int, end_tick: int) -> int:
        """Constructs an integer bitmask with bits [start_tick, end_tick) set to 1."""
        if start_tick >= end_tick or start_tick < 0:
            return 0
        return ((1 << (end_tick - start_tick)) - 1) << start_tick

    def mark_interval_busy(self, target: Any, start_tick: int, end_tick: int) -> None:
        """Marks interval [start_tick, end_tick) as busy in the target mask or collection."""
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        if isinstance(target, list):
            # Backwards compatibility if passed a boolean list
            for t in range(s, e):
                target[t] = True

    def is_interval_free(self, mask_or_list: Any, start_tick: int, end_tick: int) -> bool:
        """True if every tick in [start_tick, end_tick) is unallocated (False / 0)."""
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        if s >= e or start_tick < 0 or end_tick > self.horizon_ticks:
            return False
        if isinstance(mask_or_list, int):
            mask = self.interval_mask(s, e)
            return (mask_or_list & mask) == 0
        elif isinstance(mask_or_list, list):
            for t in range(s, e):
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
    ) -> ScheduleResult:
        """Executes deterministic earliest-fit scheduling over the snapshot state.
        
        Args:
            snapshot: Canonical validated dealership snapshot state.
            plan_id: Identifier for the candidate plan.
            evidence: Explicit operational evidence bundle (authorizations, progress, weights).
            blocked_bay_intervals: Optional external bay blocks for shadow-price re-solves.
            
        Returns:
            ScheduleResult with verified candidate plan and complete objective metrics.
        """
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

        # 3. Handle Vehicles IMMOBILIZED_ON_LIFT (C5)
        # Any vehicle trapped on a lift must retain its assigned bay exclusively
        immobilized_ros = {
            r.ro_id: r for r in snapshot.repair_orders
            if (r.physical_state.value if hasattr(r.physical_state, "value") else str(r.physical_state)) == "IMMOBILIZED_ON_LIFT"
        }
        immobilized_bay_reservations = {
            r.ro_id: r.assigned_bay_id for r in immobilized_ros.values() if r.assigned_bay_id
        }

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

        incomplete_tasks.sort(key=task_sort_key)

        # 5. Iterative Earliest-Fit Dispatching with Transitive Precedence Closure
        task_completion_ticks: Dict[str, int] = {}
        scheduled_task_ids: Set[str] = set()
        unscheduled_task_ids: Set[str] = set()

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

            # Task Execution Progress and Remaining Duration
            effective_duration = ev.get_effective_remaining_duration(
                task.task_id, task.status, task.estimated_duration_ticks
            )
            if effective_duration is None:
                unscheduled_reasons[task.task_id] = f"MISSING_EXECUTION_PROGRESS_{task.task_id}"
                unscheduled_task_ids.add(task.task_id)
                continue
            if effective_duration <= 0:
                # Completed or non-positive
                completed_task_ids.add(task.task_id)
                continue

            duration = effective_duration

            # C3 Precedence Closure Gate: If any incomplete predecessor failed to schedule, fail immediately
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

            # C5 Vehicle Physical State & Holding Staging Gate
            phys_ev = ev.vehicle_evidence.get(ro.vehicle_id) or ev.vehicle_evidence.get(ro.ro_id)
            state_val = (
                phys_ev.physical_state.value if (phys_ev and hasattr(phys_ev.physical_state, "value"))
                else (ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state))
            )
            if state_val == "UNKNOWN":
                unscheduled_reasons[task.task_id] = f"UNKNOWN_VEHICLE_STATE_{ro.ro_id}"
                unscheduled_task_ids.add(task.task_id)
                continue

            is_holding = phys_ev.is_in_holding if phys_ev else (state_val == "IN_HOLDING")
            earliest_move_tick = (ev.current_tick + 2) if is_holding else horizon_start

            earliest_possible_start = max(horizon_start, earliest_part_tick, earliest_pred_tick, earliest_move_tick)

            # C1 Skills Match: Find eligible active technicians
            eligible_techs = [
                t for t in snapshot.technicians
                if t.is_active and task.required_skill in t.skill_certifications
            ]
            if not eligible_techs:
                unscheduled_reasons[task.task_id] = f"NO_ELIGIBLE_TECHNICIAN_SKILL_{task.required_skill}"
                unscheduled_task_ids.add(task.task_id)
                continue

            # C1 Bay Compatibility & Weight Rating Gate
            vehicle_weight = (
                phys_ev.vehicle_weight_lbs
                if (phys_ev and phys_ev.vehicle_weight_lbs is not None)
                else getattr(ro, "vehicle_weight_lbs", 0)
            )

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
                for bay in compatible_bays:
                    if not grid.is_bay_free(bay.bay_id, t_start, t_end):
                        continue
                    for tech in eligible_techs:
                        if not grid.is_tech_free(tech.tech_id, t_start, t_end):
                            continue

                        # Feasible slot found! Allocate atomically
                        grid.allocate(tech.tech_id, bay.bay_id, t_start, t_end)
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

        # 6. Reconstruct Vehicle Occupancy for Immobilized Vehicles
        for imm_ro_id, imm_ro in immobilized_ros.items():
            if imm_ro.assigned_bay_id:
                imm_assignments = [a for a in assignments if a.ro_id == imm_ro_id]
                if imm_assignments:
                    first_start = min(a.start_tick for a in imm_assignments)
                    if first_start > horizon_start:
                        vehicle_occupancies.append(
                            VehicleBayOccupancy(
                                vehicle_id=imm_ro.vehicle_id,
                                ro_id=imm_ro.ro_id,
                                bay_id=imm_ro.assigned_bay_id,
                                start_tick=horizon_start,
                                end_tick=first_start,
                            )
                        )
                else:
                    vehicle_occupancies.append(
                        VehicleBayOccupancy(
                            vehicle_id=imm_ro.vehicle_id,
                            ro_id=imm_ro.ro_id,
                            bay_id=imm_ro.assigned_bay_id,
                            start_tick=horizon_start,
                            end_tick=horizon_end,
                        )
                    )

        # 7. Calculate Objective Metrics
        total_labor_ticks = sum(
            tasks_by_id[a.task_id].estimated_duration_ticks for a in assignments if a.task_id in tasks_by_id
        )
        gross_contrib = (Decimal(str(total_labor_ticks)) * self.config.labor_contribution_per_hour_usd) / Decimal("12")

        weighted_lateness_ticks = 0
        scheduled_ro_ids = {a.ro_id for a in assignments}
        for ro_id in scheduled_ro_ids:
            ro = ros_by_id[ro_id]
            ro_assignments = [a for a in assignments if a.ro_id == ro_id]
            if ro_assignments:
                completion_tick = max(a.end_tick for a in ro_assignments)
                lateness_ticks = max(0, completion_tick - ro.promise_tick)
                weighted_lateness_ticks += ro.priority_weight * lateness_ticks

        lateness_penalty = Decimal(str(weighted_lateness_ticks * 5)) * self.config.lateness_penalty_per_minute_usd

        # Calculate Avoidable Idle Bay Blocked Ticks
        bay_blocked_ticks = 0
        for occ in vehicle_occupancies:
            bay_blocked_ticks += (occ.end_tick - occ.start_tick)

        bay_blocked_penalty = Decimal(str(bay_blocked_ticks * 5)) * self.config.blocked_bay_penalty_per_minute_usd
        net_obj = gross_contrib - lateness_penalty - bay_blocked_penalty

        metrics = ObjectiveMetrics(
            gross_contribution_usd=gross_contrib.quantize(Decimal("0.01")),
            sourcing_cost_usd=Decimal("0.00"),
            weighted_lateness_ticks=weighted_lateness_ticks,
            lateness_penalty_usd=lateness_penalty.quantize(Decimal("0.01")),
            bay_blocked_ticks=bay_blocked_ticks,
            bay_blocked_penalty_usd=bay_blocked_penalty.quantize(Decimal("0.01")),
            schedule_churn_score=None,
            schedule_churn_penalty_usd=None,
            churn_status="NOT_APPLICABLE",
            net_objective_usd=net_obj.quantize(Decimal("0.01")),
            objective_completeness="PARTIAL_CONFIGURED",
            configured_terms=["gross_contribution", "lateness_penalty", "bay_blocked_penalty"],
            unconfigured_terms=["sourcing_cost", "schedule_churn_penalty"],
        )

        # 8. Candidate Schedule Plan Assembly (Explicit verified authorizations only)
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

        # 9. Dual Independent Verification: L4 Sweep-Line Oracle AND Supplemental Audit
        oracle = SweepLineOracle(snapshot)
        verification_result = oracle.verify_plan(candidate_plan)

        supp_oracle = SupplementalAuditOracle(snapshot, ev)
        supp_result = supp_oracle.audit_plan(candidate_plan)

        is_verified = verification_result.is_valid
        is_fully_certified = is_verified and supp_result.is_valid

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return ScheduleResult(
            plan_id=plan_id,
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            solver_tier=SchedulerTier.T1_HEURISTIC,
            solver_status=SolverStatus.FEASIBLE if is_verified else SolverStatus.UNKNOWN,
            runtime_ms=round(elapsed_ms, 3),
            objective_value_usd=net_obj.quantize(Decimal("0.01")),
            best_bound_usd=None,
            optimality_gap=None,
            plan=candidate_plan,
            metrics=metrics,
            unscheduled_tasks=unscheduled_reasons,
            verification_result=verification_result,
            is_verified=is_verified,
            supplemental_audit_result=supp_result.model_dump(),
            is_fully_certified=is_fully_certified,
            evidence_coverage_gaps=supp_result.coverage_gaps,
            degradation_reason=None if is_verified else f"T1 plan failed L4 verification with {verification_result.total_violations} violations",
        )
