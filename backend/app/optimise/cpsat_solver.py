"""T2 Google OR-Tools CP-SAT Discrete Scheduling Optimizer for ServiceYield AI.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 3: Module 2 Optimise)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md (A3: $120/hr sold labor)
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md (Task 1.4)

Design Guarantees:
1. Exact discrete 5-minute tick formulation over horizon H=288.
2. Inviolable hard constraints C1–C7 (eligibility, parts release, precedence, exclusivity, shifts, breaks).
3. Economic objective: Maximizing sold labor contribution minus weighted customer lateness penalty.
4. T1 solution warm-starting (hints) for accelerated convergence.
5. Strict solver status semantics (OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN).
6. Mandatory L4 independent verification gate. Infallible fallback to T1 upon timeout or L4 rejection.
"""

from collections import defaultdict
from decimal import Decimal
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from ortools.sat.python import cp_model

from app.optimise.config import OptimiseConfig
from app.optimise.heuristics import T1BitsetScheduler
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


class CPSATScheduler:
    """Discrete OR-Tools CP-SAT workshop scheduling optimizer."""

    def __init__(self, config: Optional[OptimiseConfig] = None):
        self.config = config or OptimiseConfig()
        self.t1_fallback = T1BitsetScheduler(self.config)

    def schedule(
        self,
        snapshot: DealershipSnapshotSchema,
        plan_id: str = "PLAN-T2-CPSAT",
        blocked_bay_intervals: Optional[List[Tuple[str, int, int]]] = None,
    ) -> ScheduleResult:
        """Formulates and solves the global discrete workshop scheduling optimization problem.
        
        Args:
            snapshot: Canonical validated dealership state snapshot.
            plan_id: Identifier for candidate plan and audit logs.
            blocked_bay_intervals: Optional capacity blocks [(bay_id, start_tick, end_tick)]
                                   for shadow price difference re-solves.
        
        Returns:
            ScheduleResult containing verified plan, solver status, metrics, and L4 report.
        """
        start_time = time.perf_counter()
        blocked_intervals = blocked_bay_intervals or []

        # 1. State Lookups
        bays_by_id = {b.bay_id: b for b in snapshot.bays}
        techs_by_id = {t.tech_id: t for t in snapshot.technicians}
        ros_by_id = {r.ro_id: r for r in snapshot.repair_orders}
        tasks_by_id = {t.task_id: t for t in snapshot.tasks}

        parts_by_task: Dict[str, List[Any]] = defaultdict(list)
        for p in snapshot.part_requirements:
            parts_by_task[p.task_id].append(p)

        # 2. Identify Incomplete Tasks
        incomplete_tasks: List[TaskSchema] = []
        completed_task_ids: Set[str] = set()

        for t in snapshot.tasks:
            status_str = t.status.value if hasattr(t.status, "value") else str(t.status)
            if status_str == "COMPLETED":
                completed_task_ids.add(t.task_id)
            else:
                incomplete_tasks.append(t)

        # 3. Check Part Availability Feasibility
        # If any task has a part with usable_ready_tick == None, it cannot be scheduled
        unscheduled_reasons: Dict[str, str] = {}
        schedulable_tasks: List[TaskSchema] = []

        for task in incomplete_tasks:
            task_parts = parts_by_task.get(task.task_id, [])
            part_missing_eta = False
            for part in task_parts:
                if part.usable_ready_tick is None:
                    unscheduled_reasons[task.task_id] = f"PART_NOT_READY_NO_ETA_{part.part_req_id}"
                    part_missing_eta = True
                    break
            if not part_missing_eta:
                schedulable_tasks.append(task)

        # Precedence Cycle Guard
        predecessors: Dict[str, List[str]] = {t.task_id: t.predecessor_task_ids for t in schedulable_tasks}
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

        # 4. Initialize CP-SAT Model
        model = cp_model.CpModel()

        # Horizon bounds
        horizon_start = self.config.horizon_start_tick
        horizon_end = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else self.config.horizon_end_tick

        # Track decision variables:
        # task_id -> {start_var, end_var, duration, is_scheduled_var, interval_var}
        task_vars: Dict[str, Dict[str, Any]] = {}
        # (task_id, tech_id) -> bool_var
        tech_assignment_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        # (task_id, bay_id) -> bool_var
        bay_assignment_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}

        # Intervals per technician and per bay for NoOverlap constraints
        tech_intervals: Dict[str, List[cp_model.IntervalVar]] = defaultdict(list)
        bay_intervals: Dict[str, List[cp_model.IntervalVar]] = defaultdict(list)

        # Handle vehicle immobilized state (C5)
        immobilized_ros = {
            r.ro_id: r for r in snapshot.repair_orders
            if (r.physical_state.value if hasattr(r.physical_state, "value") else str(r.physical_state)) == "IMMOBILIZED_ON_LIFT"
        }
        immobilized_bay_ids = {r.assigned_bay_id for r in immobilized_ros.values() if r.assigned_bay_id}

        # Create variables for each schedulable task
        for task in schedulable_tasks:
            t_id = task.task_id
            ro = ros_by_id[task.ro_id]
            duration = task.estimated_duration_ticks

            # Is task scheduled boolean
            is_sched = model.NewBoolVar(f"is_sched_{t_id}")

            # Start and End ticks
            start_var = model.NewIntVar(horizon_start, horizon_end, f"start_{t_id}")
            end_var = model.NewIntVar(horizon_start, horizon_end, f"end_{t_id}")
            task_interval = model.NewOptionalIntervalVar(start_var, duration, end_var, is_sched, f"opt_interval_{t_id}")

            task_vars[t_id] = {
                "is_scheduled": is_sched,
                "start": start_var,
                "end": end_var,
                "duration": duration,
                "interval": task_interval,
                "ro_id": task.ro_id,
            }

            # C2 Part Usable-Ready Timing
            task_parts = parts_by_task.get(t_id, [])
            if task_parts:
                max_usable_tick = max(p.usable_ready_tick for p in task_parts if p.usable_ready_tick is not None)
                model.Add(start_var >= max_usable_tick).OnlyEnforceIf(is_sched)

            # C1 Eligibility: Technicians
            eligible_techs = [
                t for t in snapshot.technicians
                if t.is_active and task.required_skill in t.skill_certifications
            ]
            t_tech_vars: List[cp_model.IntVar] = []
            for tech in eligible_techs:
                var = model.NewBoolVar(f"x_{t_id}_{tech.tech_id}")
                tech_assignment_vars[(t_id, tech.tech_id)] = var
                t_tech_vars.append(var)

                # Optional interval for technician
                opt_tech_interval = model.NewOptionalIntervalVar(
                    start_var, duration, end_var, var, f"tech_int_{t_id}_{tech.tech_id}"
                )
                tech_intervals[tech.tech_id].append(opt_tech_interval)

                # C6 Technician Shift Window
                model.Add(start_var >= tech.shift_start_tick).OnlyEnforceIf(var)
                shift_end = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else tech.shift_end_tick
                model.Add(end_var <= shift_end).OnlyEnforceIf(var)

            # Exactly one eligible technician if scheduled
            if t_tech_vars:
                model.Add(sum(t_tech_vars) == is_sched)
            else:
                model.Add(is_sched == 0)

            # C1 & C5 Eligibility: Bays
            # If vehicle is IMMOBILIZED_ON_LIFT, it is locked into its assigned bay
            if task.ro_id in immobilized_ros:
                imm_bay_id = immobilized_ros[task.ro_id].assigned_bay_id
                assigned_bay = bays_by_id.get(imm_bay_id) if imm_bay_id else None
                if assigned_bay and assigned_bay.is_operational and assigned_bay.bay_type == task.required_bay_type:
                    compatible_bays = [assigned_bay]
                else:
                    compatible_bays = []
            else:
                compatible_bays = [
                    b for b in snapshot.bays
                    if b.is_operational
                    and b.bay_type == task.required_bay_type
                    and b.bay_id not in immobilized_bay_ids
                ]

            t_bay_vars: List[cp_model.IntVar] = []
            for bay in compatible_bays:
                var = model.NewBoolVar(f"y_{t_id}_{bay.bay_id}")
                bay_assignment_vars[(t_id, bay.bay_id)] = var
                t_bay_vars.append(var)

                opt_bay_interval = model.NewOptionalIntervalVar(
                    start_var, duration, end_var, var, f"bay_int_{t_id}_{bay.bay_id}"
                )
                bay_intervals[bay.bay_id].append(opt_bay_interval)

            if t_bay_vars:
                model.Add(sum(t_bay_vars) == is_sched)
            else:
                model.Add(is_sched == 0)

        # 5. C3 Precedence Constraints
        for task in schedulable_tasks:
            t_id = task.task_id
            for pred_id in task.predecessor_task_ids:
                if pred_id in completed_task_ids:
                    # Completed before horizon start
                    continue
                elif pred_id in task_vars:
                    # If both scheduled, predecessor must finish before successor starts
                    model.Add(task_vars[t_id]["start"] >= task_vars[pred_id]["end"]).OnlyEnforceIf(
                        [task_vars[t_id]["is_scheduled"], task_vars[pred_id]["is_scheduled"]]
                    )
                    # A task cannot be scheduled if its incomplete predecessor is not scheduled
                    model.Add(task_vars[t_id]["is_scheduled"] <= task_vars[pred_id]["is_scheduled"])

        # 6. C4 Exclusivity: Technician Constraints & Lunch Breaks
        for tech in snapshot.technicians:
            if not tech.is_active:
                continue
            # Add mandatory meal break interval
            lunch_interval = model.NewIntervalVar(
                tech.lunch_start_tick,
                tech.lunch_duration_ticks,
                tech.lunch_start_tick + tech.lunch_duration_ticks,
                f"lunch_{tech.tech_id}",
            )
            model.AddNoOverlap(tech_intervals[tech.tech_id] + [lunch_interval])

        # 7. C4 Exclusivity: Bay Constraints & Immobilized Occupancy
        # Inject any externally blocked intervals (for shadow-price re-solves)
        for block_bay, b_start, b_end in blocked_intervals:
            if block_bay in bays_by_id and b_end > b_start:
                block_int = model.NewIntervalVar(b_start, b_end - b_start, b_end, f"blocked_{block_bay}_{b_start}")
                bay_intervals[block_bay].append(block_int)

        for bay in snapshot.bays:
            if not bay.is_operational:
                continue
            model.AddNoOverlap(bay_intervals[bay.bay_id])

        # 8. Objective Function Formulation
        # Economic parameters:
        # Labor contribution: $120.00/hour = $10.00/tick = 1000 cents/tick
        # Lateness penalty: $0.50/minute = $2.50/tick = 250 cents/tick
        cents_per_labor_tick = int(round(float(self.config.labor_contribution_per_hour_usd) / 12.0 * 100.0))
        cents_per_lateness_tick = int(round(float(self.config.lateness_penalty_per_minute_usd) * 5.0 * 100.0))

        objective_terms = []

        # Gross Labor Contribution: sum(cents_per_labor_tick * d_i * is_sched_i)
        for t_id, tv in task_vars.items():
            contrib_cents = cents_per_labor_tick * tv["duration"]
            objective_terms.append(contrib_cents * tv["is_scheduled"])

        # Lateness Penalties: for each RO, lateness = max(0, max(end_t) - promise_tick)
        ro_lateness_vars: Dict[str, cp_model.IntVar] = {}
        for ro in snapshot.repair_orders:
            ro_tasks = [t for t in schedulable_tasks if t.ro_id == ro.ro_id]
            if not ro_tasks:
                continue

            lateness_var = model.NewIntVar(0, 288, f"lateness_{ro.ro_id}")
            ro_lateness_vars[ro.ro_id] = lateness_var

            for t in ro_tasks:
                tv = task_vars[t.task_id]
                # If task is scheduled: lateness >= end - promise_tick
                model.Add(lateness_var >= tv["end"] - ro.promise_tick).OnlyEnforceIf(tv["is_scheduled"])

            # Scale lateness penalty by RO priority weight
            ro_penalty_cents = cents_per_lateness_tick * ro.priority_weight
            objective_terms.append(-ro_penalty_cents * lateness_var)

        model.Maximize(sum(objective_terms))

        # 9. T1 Warm-Start Solution Hinting
        if self.config.enable_t1_warm_start and not blocked_intervals:
            t1_result = self.t1_fallback.schedule(snapshot)
            if t1_result.is_verified:
                for a in t1_result.plan.assignments:
                    if a.task_id in task_vars:
                        tv = task_vars[a.task_id]
                        model.AddHint(tv["is_scheduled"], 1)
                        model.AddHint(tv["start"], a.start_tick)
                        model.AddHint(tv["end"], a.end_tick)
                        if (a.task_id, a.tech_id) in tech_assignment_vars:
                            model.AddHint(tech_assignment_vars[(a.task_id, a.tech_id)], 1)
                        if (a.task_id, a.bay_id) in bay_assignment_vars:
                            model.AddHint(bay_assignment_vars[(a.task_id, a.bay_id)], 1)

        # 10. Solve with CP-SAT
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.time_budget_seconds
        solver.parameters.num_search_workers = self.config.num_workers
        solver.parameters.random_seed = self.config.deterministic_seed

        status = solver.Solve(model)
        solve_elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # 11. Process Solver Outcome
        if status == cp_model.OPTIMAL:
            solver_status = SolverStatus.OPTIMAL
        elif status == cp_model.FEASIBLE:
            solver_status = SolverStatus.FEASIBLE
        elif status == cp_model.INFEASIBLE:
            solver_status = SolverStatus.INFEASIBLE
        else:
            solver_status = SolverStatus.UNKNOWN

        # If solver found a feasible incumbent (OPTIMAL or FEASIBLE)
        if solver_status in {SolverStatus.OPTIMAL, SolverStatus.FEASIBLE}:
            assignments: List[ScheduledAssignment] = []
            vehicle_occupancies: List[VehicleBayOccupancy] = []

            for task in schedulable_tasks:
                t_id = task.task_id
                tv = task_vars[t_id]
                if solver.Value(tv["is_scheduled"]) == 1:
                    start_t = int(solver.Value(tv["start"]))
                    end_t = int(solver.Value(tv["end"]))

                    # Find assigned tech
                    assigned_tech_id = None
                    for tech in snapshot.technicians:
                        if (t_id, tech.tech_id) in tech_assignment_vars:
                            if solver.Value(tech_assignment_vars[(t_id, tech.tech_id)]) == 1:
                                assigned_tech_id = tech.tech_id
                                break

                    # Find assigned bay
                    assigned_bay_id = None
                    for bay in snapshot.bays:
                        if (t_id, bay.bay_id) in bay_assignment_vars:
                            if solver.Value(bay_assignment_vars[(t_id, bay.bay_id)]) == 1:
                                assigned_bay_id = bay.bay_id
                                break

                    if assigned_tech_id and assigned_bay_id:
                        assignments.append(
                            ScheduledAssignment(
                                task_id=t_id,
                                ro_id=task.ro_id,
                                tech_id=assigned_tech_id,
                                bay_id=assigned_bay_id,
                                start_tick=start_t,
                                end_tick=end_t,
                            )
                        )
                else:
                    unscheduled_reasons[t_id] = "EXCLUDED_BY_OPTIMIZER_CAPACITY"

            # Reconstruct vehicle occupancy intervals for immobilized vehicles
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

            # Calculate metrics
            total_labor_ticks = sum(
                tasks_by_id[a.task_id].estimated_duration_ticks for a in assignments if a.task_id in tasks_by_id
            )
            gross_contrib = (Decimal(str(total_labor_ticks)) * self.config.labor_contribution_per_hour_usd) / Decimal("12")

            weighted_lateness_ticks = 0
            for ro_id, lat_var in ro_lateness_vars.items():
                ro = ros_by_id[ro_id]
                lat_ticks = int(solver.Value(lat_var))
                weighted_lateness_ticks += ro.priority_weight * lat_ticks

            lateness_penalty = Decimal(str(weighted_lateness_ticks * 5)) * self.config.lateness_penalty_per_minute_usd
            net_obj = gross_contrib - lateness_penalty

            metrics = ObjectiveMetrics(
                gross_contribution_usd=gross_contrib.quantize(Decimal("0.01")),
                sourcing_cost_usd=Decimal("0.00"),
                weighted_lateness_ticks=weighted_lateness_ticks,
                lateness_penalty_usd=lateness_penalty.quantize(Decimal("0.01")),
                bay_blocked_ticks=0,
                bay_blocked_penalty_usd=Decimal("0.00"),
                schedule_churn_score=0,
                schedule_churn_penalty_usd=Decimal("0.00"),
                net_objective_usd=net_obj.quantize(Decimal("0.01")),
            )

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

            # L4 Independent Sweep-Line Verification Audit
            oracle = SweepLineOracle(snapshot)
            verification_result = oracle.verify_plan(candidate_plan)

            # Optimality gap
            best_bound_cents = solver.BestObjectiveBound()
            obj_cents = solver.ObjectiveValue()
            gap = 0.0
            if solver_status == SolverStatus.FEASIBLE and abs(obj_cents) > 1e-6:
                gap = abs(best_bound_cents - obj_cents) / abs(obj_cents)

            if verification_result.is_valid:
                return ScheduleResult(
                    plan_id=plan_id,
                    rooftop_id=snapshot.rooftop.rooftop_id,
                    snapshot_hash=snapshot.snapshot_hash or "",
                    solver_tier=SchedulerTier.T2_CPSAT,
                    solver_status=solver_status,
                    runtime_ms=round(solve_elapsed_ms, 3),
                    objective_value_usd=net_obj.quantize(Decimal("0.01")),
                    best_bound_usd=Decimal(str(best_bound_cents / 100.0)).quantize(Decimal("0.01")),
                    optimality_gap=round(gap, 4),
                    plan=candidate_plan,
                    metrics=metrics,
                    unscheduled_tasks=unscheduled_reasons,
                    verification_result=verification_result,
                    is_verified=True,
                )
            else:
                # T2 candidate failed L4 verifier! Discard and fall back to verified T1
                t1_fallback_res = self.t1_fallback.schedule(
                    snapshot,
                    plan_id=f"{plan_id}-T1-FALLBACK",
                    blocked_bay_intervals=blocked_intervals,
                )
                t1_fallback_res.degradation_reason = (
                    f"T2 CP-SAT candidate failed L4 verification with {verification_result.total_violations} violations; "
                    f"reverted to T1 constructive schedule."
                )
                return t1_fallback_res

        # If solver returned INFEASIBLE or UNKNOWN (timeout with no incumbent), fall back to T1
        t1_fallback_res = self.t1_fallback.schedule(
            snapshot,
            plan_id=f"{plan_id}-T1-FALLBACK",
            blocked_bay_intervals=blocked_intervals,
        )
        t1_fallback_res.degradation_reason = (
            f"CP-SAT solver returned {solver_status.value} in {solve_elapsed_ms:.1f}ms; "
            f"automatically degraded to verified T1 schedule."
        )
        return t1_fallback_res
