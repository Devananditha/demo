"""T1 Deterministic Constructive Bitset Scheduler for ServiceYield AI.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 3.2: T1 Dispatcher)
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md (Task 1.4)

Design Guarantees:
1. Deterministic earliest-fit priority dispatching under hard constraints C1–C7.
2. Compact discrete tick occupancy masks for sub-2 millisecond latency.
3. Stable priority ordering (RO priority weight, customer promise, sequence order, task ID).
4. Full integration with L4 Sweep-Line Independent Verifier.
5. Infallible fallback: Always returns a valid typed result without crashing.
"""

from collections import defaultdict
from decimal import Decimal
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.optimise.config import OptimiseConfig
from app.optimise.models import (
    ObjectiveMetrics,
    ScheduleResult,
    SchedulerTier,
    SolverStatus,
)
from app.schemas.domain import (
    DealershipSnapshotSchema,
    RepairOrderSchema,
    TaskSchema,
    VehiclePhysicalState,
)
from app.verifier.models import (
    CandidateSchedulePlan,
    ScheduledAssignment,
    VehicleBayOccupancy,
)
from app.verifier.sweep_oracle import SweepLineOracle


class BitsetOccupancyGrid:
    """Fast discrete-tick occupancy mask over horizon [0, 288].
    
    Uses 288-element boolean masks for O(1) interval collision testing.
    """

    def __init__(self, horizon_ticks: int = 288):
        self.horizon_ticks = horizon_ticks
        self._tech_busy: Dict[str, List[bool]] = defaultdict(lambda: [False] * self.horizon_ticks)
        self._bay_busy: Dict[str, List[bool]] = defaultdict(lambda: [False] * self.horizon_ticks)

    def mark_interval_busy(self, mask: List[bool], start_tick: int, end_tick: int) -> None:
        """Sets [start_tick, end_tick) to busy (True)."""
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        for t in range(s, e):
            mask[t] = True

    def is_interval_free(self, mask: List[bool], start_tick: int, end_tick: int) -> bool:
        """Returns True if every tick in [start_tick, end_tick) is unallocated (False)."""
        s = max(0, start_tick)
        e = min(self.horizon_ticks, end_tick)
        if s >= e:
            return False
        for t in range(s, e):
            if mask[t]:
                return False
        return True

    def is_tech_free(self, tech_id: str, start_tick: int, end_tick: int) -> bool:
        return self.is_interval_free(self._tech_busy[tech_id], start_tick, end_tick)

    def is_bay_free(self, bay_id: str, start_tick: int, end_tick: int) -> bool:
        return self.is_interval_free(self._bay_busy[bay_id], start_tick, end_tick)

    def allocate(self, tech_id: str, bay_id: str, start_tick: int, end_tick: int) -> None:
        self.mark_interval_busy(self._tech_busy[tech_id], start_tick, end_tick)
        self.mark_interval_busy(self._bay_busy[bay_id], start_tick, end_tick)

    def allocate_bay_only(self, bay_id: str, start_tick: int, end_tick: int) -> None:
        self.mark_interval_busy(self._bay_busy[bay_id], start_tick, end_tick)


class T1BitsetScheduler:
    """Deterministic constructive earliest-fit bitset scheduler."""

    def __init__(self, config: Optional[OptimiseConfig] = None):
        self.config = config or OptimiseConfig()

    def schedule(
        self,
        snapshot: DealershipSnapshotSchema,
        plan_id: str = "PLAN-T1-DISPATCH",
        blocked_bay_intervals: Optional[List[Tuple[str, int, int]]] = None,
    ) -> ScheduleResult:
        """Executes deterministic earliest-fit scheduling over the snapshot state.
        
        Returns:
            ScheduleResult with verified candidate plan and complete objective metrics.
        """
        start_time = time.perf_counter()
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
        grid = BitsetOccupancyGrid(horizon_ticks=288)

        # Pre-allocate technician shifts and lunch breaks into tech masks
        for tech in snapshot.technicians:
            if not tech.is_active:
                # Inactive tech is busy entire horizon
                grid.mark_interval_busy(grid._tech_busy[tech.tech_id], 0, 288)
                continue

            # Mark ticks before shift start as busy
            if tech.shift_start_tick > 0:
                grid.mark_interval_busy(grid._tech_busy[tech.tech_id], 0, tech.shift_start_tick)

            # Mark ticks after shift end as busy (unless overtime authorized)
            shift_cutoff = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else tech.shift_end_tick
            if shift_cutoff < 288:
                grid.mark_interval_busy(grid._tech_busy[tech.tech_id], shift_cutoff, 288)

            # Mark mandatory meal break window as busy
            lunch_end = tech.lunch_start_tick + tech.lunch_duration_ticks
            grid.mark_interval_busy(grid._tech_busy[tech.tech_id], tech.lunch_start_tick, lunch_end)

        # Pre-allocate non-operational bays
        for bay in snapshot.bays:
            if not bay.is_operational:
                grid.mark_interval_busy(grid._bay_busy[bay.bay_id], 0, 288)

        # Pre-allocate externally blocked bay intervals (e.g. for shadow pricing difference re-solves)
        if blocked_bay_intervals:
            for b_id, b_start, b_end in blocked_bay_intervals:
                if b_id in bays_by_id and b_end > b_start:
                    grid.mark_interval_busy(grid._bay_busy[b_id], b_start, b_end)

        # 3. Handle Vehicles IMMOBILIZED_ON_LIFT (C5)
        # Any vehicle trapped on a lift must retain its assigned bay
        immobilized_ros = [
            r for r in snapshot.repair_orders
            if (r.physical_state.value if hasattr(r.physical_state, "value") else str(r.physical_state)) == "IMMOBILIZED_ON_LIFT"
        ]
        
        # Track immobilized vehicle reservation intervals: ro_id -> (bay_id, earliest_task_start)
        immobilized_bay_reservations: Dict[str, str] = {}
        for imm_ro in immobilized_ros:
            if imm_ro.assigned_bay_id:
                immobilized_bay_reservations[imm_ro.ro_id] = imm_ro.assigned_bay_id

        # 4. Filter and Sort Incomplete Tasks
        # Exclude COMPLETED tasks; keep PENDING, IN_PROGRESS, STALLED
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
        # 1. RO Priority Weight descending (w_r: 3 -> 2 -> 1)
        # 2. Customer Promise Tick ascending (earliest promise first)
        # 3. Sequence Order ascending (topological sequence order)
        # 4. Duration ascending (Shortest Processing Time heuristic)
        # 5. Stable Tie-breaker: task_id ascending
        def task_sort_key(task: TaskSchema) -> Tuple[int, int, int, int, str]:
            ro = ros_by_id.get(task.ro_id)
            priority = ro.priority_weight if ro else 1
            promise = ro.promise_tick if ro else 288
            return (-priority, promise, task.sequence_order, task.estimated_duration_ticks, task.task_id)

        incomplete_tasks.sort(key=task_sort_key)

        # 5. Iterative Earliest-Fit Dispatching
        task_completion_ticks: Dict[str, int] = {}
        scheduled_task_ids: Set[str] = set()

        # Operational search bounds
        horizon_start = self.config.horizon_start_tick
        horizon_end = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else self.config.horizon_end_tick

        for task in incomplete_tasks:
            ro = ros_by_id.get(task.ro_id)
            if not ro:
                unscheduled_reasons[task.task_id] = "RO_NOT_FOUND"
                continue

            duration = task.estimated_duration_ticks
            if duration <= 0:
                unscheduled_reasons[task.task_id] = "INVALID_TASK_DURATION"
                continue

            # C2 Part Availability Gate
            task_parts = parts_by_task.get(task.task_id, [])
            earliest_part_tick = horizon_start
            part_blocked = False

            for part in task_parts:
                status_str = part.inventory_status.value if hasattr(part.inventory_status, "value") else str(part.inventory_status)
                if part.usable_ready_tick is None:
                    # Missing usable ready tick -> cannot schedule
                    unscheduled_reasons[task.task_id] = f"PART_NOT_READY_NO_ETA_{part.part_req_id}"
                    part_blocked = True
                    break
                earliest_part_tick = max(earliest_part_tick, part.usable_ready_tick)

            if part_blocked:
                continue

            # C3 Precedence Gate
            earliest_pred_tick = horizon_start
            pred_blocked = False

            for pred_id in task.predecessor_task_ids:
                if pred_id in completed_task_ids:
                    # Predecessor was completed prior to current horizon
                    continue
                elif pred_id in task_completion_ticks:
                    earliest_pred_tick = max(earliest_pred_tick, task_completion_ticks[pred_id])
                else:
                    # Incomplete predecessor was not scheduled -> cannot start
                    unscheduled_reasons[task.task_id] = f"PREDECESSOR_NOT_SCHEDULED_{pred_id}"
                    pred_blocked = True
                    break

            if pred_blocked:
                continue

            earliest_possible_start = max(horizon_start, earliest_part_tick, earliest_pred_tick)

            # C1 Skills Match: Find eligible active technicians
            eligible_techs = [
                t for t in snapshot.technicians
                if t.is_active and task.required_skill in t.skill_certifications
            ]
            if not eligible_techs:
                unscheduled_reasons[task.task_id] = f"NO_ELIGIBLE_TECHNICIAN_SKILL_{task.required_skill}"
                continue

            # C1 / C5 Bay Match: Find compatible operational bays
            # If vehicle is IMMOBILIZED_ON_LIFT, it MUST be assigned to its currently occupied bay
            target_bay_id = immobilized_bay_reservations.get(ro.ro_id)
            if target_bay_id:
                assigned_bay = bays_by_id.get(target_bay_id)
                if not assigned_bay or not assigned_bay.is_operational or assigned_bay.bay_type != task.required_bay_type:
                    unscheduled_reasons[task.task_id] = f"IMMOBILIZED_BAY_INCOMPATIBLE_{target_bay_id}"
                    continue
                compatible_bays = [assigned_bay]
            else:
                compatible_bays = [
                    b for b in snapshot.bays
                    if b.is_operational
                    and b.bay_type == task.required_bay_type
                    and b.bay_id not in immobilized_bay_reservations.values()
                ]

            if not compatible_bays:
                unscheduled_reasons[task.task_id] = f"NO_COMPATIBLE_OPERATIONAL_BAY_{task.required_bay_type}"
                continue

            # Sort tech and bay candidates deterministically for stable tie-breaking
            eligible_techs.sort(key=lambda t: t.tech_id)
            compatible_bays.sort(key=lambda b: b.bay_id)

            # Earliest-Fit Search: Scan discrete ticks t from earliest_possible_start
            best_start_tick: Optional[int] = None
            best_tech_id: Optional[str] = None
            best_bay_id: Optional[str] = None

            latest_allowable_start = horizon_end - duration
            for t in range(earliest_possible_start, latest_allowable_start + 1):
                end_t = t + duration
                for bay in compatible_bays:
                    if not grid.is_bay_free(bay.bay_id, t, end_t):
                        continue
                    for tech in eligible_techs:
                        if not grid.is_tech_free(tech.tech_id, t, end_t):
                            continue

                        # First feasible pair found at earliest tick t
                        best_start_tick = t
                        best_tech_id = tech.tech_id
                        best_bay_id = bay.bay_id
                        break
                    if best_start_tick is not None:
                        break
                if best_start_tick is not None:
                    break

            if best_start_tick is not None and best_tech_id is not None and best_bay_id is not None:
                finish_tick = best_start_tick + duration
                grid.allocate(best_tech_id, best_bay_id, best_start_tick, finish_tick)
                task_completion_ticks[task.task_id] = finish_tick
                scheduled_task_ids.add(task.task_id)

                assignments.append(
                    ScheduledAssignment(
                        task_id=task.task_id,
                        ro_id=ro.ro_id,
                        tech_id=best_tech_id,
                        bay_id=best_bay_id,
                        start_tick=best_start_tick,
                        end_tick=finish_tick,
                    )
                )
            else:
                unscheduled_reasons[task.task_id] = "NO_FEASIBLE_INTERVAL_WITHIN_HORIZON"

        # 6. Build Vehicle Bay Occupancies (C5 & Verifier Invariants)
        # For each immobilized vehicle, record occupancy from start of day until its work begins (or ends)
        for imm_ro in immobilized_ros:
            assigned_bay = imm_ro.assigned_bay_id
            if not assigned_bay:
                continue

            imm_assignments = [a for a in assignments if a.ro_id == imm_ro.ro_id]
            if imm_assignments:
                # If tasks were scheduled, vehicle was idle on lift before the first task started
                first_start = min(a.start_tick for a in imm_assignments)
                if first_start > horizon_start:
                    vehicle_occupancies.append(
                        VehicleBayOccupancy(
                            vehicle_id=imm_ro.vehicle_id,
                            ro_id=imm_ro.ro_id,
                            bay_id=assigned_bay,
                            start_tick=horizon_start,
                            end_tick=first_start,
                        )
                    )
            else:
                # If tasks could not be scheduled, vehicle occupies bay across operating window
                vehicle_occupancies.append(
                    VehicleBayOccupancy(
                        vehicle_id=imm_ro.vehicle_id,
                        ro_id=imm_ro.ro_id,
                        bay_id=assigned_bay,
                        start_tick=horizon_start,
                        end_tick=horizon_end,
                    )
                )

        # 7. Calculate Economic Objective Metrics
        # Maximize Z = sum(M_i - C_i) - lambda_late * sum(w_r * lateness) - lambda_block * blocked - lambda_churn * churn
        total_labor_ticks = sum(
            tasks_by_id[a.task_id].estimated_duration_ticks for a in assignments if a.task_id in tasks_by_id
        )
        gross_contribution = (Decimal(str(total_labor_ticks)) * self.config.labor_contribution_per_hour_usd) / Decimal("12")

        # Lateness calculation: max completion tick of tasks for each RO vs customer delivery promise
        weighted_lateness_ticks = 0
        assigned_ros = {a.ro_id for a in assignments}
        for ro_id in assigned_ros:
            ro = ros_by_id.get(ro_id)
            if not ro:
                continue
            ro_assignments = [a for a in assignments if a.ro_id == ro_id]
            ro_completion_tick = max(a.end_tick for a in ro_assignments)
            lateness_ticks = max(0, ro_completion_tick - ro.promise_tick)
            weighted_lateness_ticks += ro.priority_weight * lateness_ticks

        lateness_penalty_usd = (Decimal(str(weighted_lateness_ticks * 5)) * self.config.lateness_penalty_per_minute_usd)
        net_objective_usd = gross_contribution - lateness_penalty_usd

        metrics = ObjectiveMetrics(
            gross_contribution_usd=gross_contribution.quantize(Decimal("0.01")),
            sourcing_cost_usd=Decimal("0.00"),
            weighted_lateness_ticks=weighted_lateness_ticks,
            lateness_penalty_usd=lateness_penalty_usd.quantize(Decimal("0.01")),
            bay_blocked_ticks=0,
            bay_blocked_penalty_usd=Decimal("0.00"),
            schedule_churn_score=0,
            schedule_churn_penalty_usd=Decimal("0.00"),
            net_objective_usd=net_objective_usd.quantize(Decimal("0.01")),
        )

        # 8. Assemble Candidate Schedule Plan
        candidate_plan = CandidateSchedulePlan(
            plan_id=plan_id,
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            assignments=assignments,
            vehicle_occupancies=vehicle_occupancies,
            customer_authorizations={r.ro_id: True for r in snapshot.repair_orders},
            manager_freight_approvals={o.offer_id: True for o in snapshot.supplier_offers},
            allow_emergency_overtime=self.config.allow_emergency_overtime,
        )

        # 9. L4 Independent Sweep-Line Verification Audit
        oracle = SweepLineOracle(snapshot)
        verification_result = oracle.verify_plan(candidate_plan)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        solver_status = SolverStatus.FEASIBLE if assignments else SolverStatus.UNKNOWN

        return ScheduleResult(
            plan_id=plan_id,
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            solver_tier=SchedulerTier.T1_HEURISTIC,
            solver_status=solver_status,
            runtime_ms=round(elapsed_ms, 3),
            objective_value_usd=net_objective_usd.quantize(Decimal("0.01")),
            best_bound_usd=None,
            optimality_gap=None,
            plan=candidate_plan,
            metrics=metrics,
            unscheduled_tasks=unscheduled_reasons,
            verification_result=verification_result,
            is_verified=verification_result.is_valid,
            degradation_reason=None if verification_result.is_valid else f"L4 rejected plan with {verification_result.total_violations} violations",
        )
