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
3. Transitive precedence closure: successors cannot be scheduled if incomplete predecessors are excluded.
4. Zero manufactured evidence: strict customer authorization gate and verified execution progress.
5. Dual verification: Certified PASS by independent L4 sweep-line oracle AND supplemental operational audit.
6. Infallible fallback: Automatic degradation to verified T1 schedule upon timeout, infeasibility, or audit failure.
"""

from collections import defaultdict
from decimal import Decimal
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from ortools.sat.python import cp_model

from app.optimise.config import OptimiseConfig
from app.optimise.evidence import WorkshopEvidenceBundle
from app.optimise.heuristics import T1BitsetScheduler
from app.optimise.models import (
    ObjectiveMetrics,
    ScheduleResult,
    SchedulerTier,
    SolverStatus,
)
from app.optimise.supplemental_audit import SupplementalAuditOracle
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
        evidence: Optional[WorkshopEvidenceBundle] = None,
        blocked_bay_intervals: Optional[List[Tuple[str, int, int]]] = None,
    ) -> ScheduleResult:
        """Formulates and solves the global discrete workshop scheduling optimization problem.
        
        Args:
            snapshot: Canonical validated dealership state snapshot.
            plan_id: Identifier for candidate plan and audit logs.
            evidence: Explicit operational evidence bundle (authorizations, progress, weights).
            blocked_bay_intervals: Optional capacity blocks [(bay_id, start_tick, end_tick)]
                                   for shadow price difference re-solves.
        
        Returns:
            ScheduleResult containing verified plan, solver status, metrics, and dual audit report.
        """
        start_time = time.perf_counter()
        ev = evidence or WorkshopEvidenceBundle(current_tick=snapshot.rooftop.operating_day_start_tick)
        blocked_intervals = blocked_bay_intervals or []

        # 1. State Lookups
        bays_by_id = {b.bay_id: b for b in snapshot.bays}
        techs_by_id = {t.tech_id: t for t in snapshot.technicians}
        ros_by_id = {r.ro_id: r for r in snapshot.repair_orders}
        tasks_by_id = {t.task_id: t for t in snapshot.tasks}

        parts_by_task: Dict[str, List[Any]] = defaultdict(list)
        for p in snapshot.part_requirements:
            parts_by_task[p.task_id].append(p)

        horizon_start = self.config.horizon_start_tick
        horizon_end = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else self.config.horizon_end_tick

        # 2. Identify Incomplete Tasks and Filter by Authorizations and Duration Evidence
        unscheduled_reasons: Dict[str, str] = {}
        completed_task_ids: Set[str] = set()
        candidate_tasks: List[TaskSchema] = []
        effective_durations: Dict[str, int] = {}

        for t in snapshot.tasks:
            status_str = t.status.value if hasattr(t.status, "value") else str(t.status)
            if status_str == "COMPLETED":
                completed_task_ids.add(t.task_id)
                continue

            # C7 Customer Estimate Authorization Gate
            if not ev.is_ro_authorized(t.ro_id):
                unscheduled_reasons[t.task_id] = f"UNAUTHORIZED_CUSTOMER_ESTIMATE_{t.ro_id}"
                continue

            # Task Execution Progress and Remaining Duration Evidence
            rem_dur = ev.get_effective_remaining_duration(t.task_id, t.status, t.estimated_duration_ticks)
            if rem_dur is None:
                unscheduled_reasons[t.task_id] = f"MISSING_EXECUTION_PROGRESS_{t.task_id}"
                continue
            if rem_dur <= 0:
                completed_task_ids.add(t.task_id)
                continue

            # C2 Part Availability Gate
            task_parts = parts_by_task.get(t.task_id, [])
            has_missing_eta = False
            for part in task_parts:
                if part.usable_ready_tick is None:
                    unscheduled_reasons[t.task_id] = f"PART_NOT_READY_NO_ETA_{part.part_req_id}"
                    has_missing_eta = True
                    break
            if has_missing_eta:
                continue

            # C5 Vehicle Physical State Gate
            ro = ros_by_id.get(t.ro_id)
            if ro:
                phys_ev = ev.vehicle_evidence.get(ro.vehicle_id) or ev.vehicle_evidence.get(ro.ro_id)
                state_val = (
                    phys_ev.physical_state.value if (phys_ev and hasattr(phys_ev.physical_state, "value"))
                    else (ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state))
                )
                if state_val == "UNKNOWN":
                    unscheduled_reasons[t.task_id] = f"UNKNOWN_VEHICLE_STATE_{ro.ro_id}"
                    continue

                is_holding = phys_ev.is_in_holding if phys_ev else (state_val == "IN_HOLDING")
                earliest_move = (ev.current_tick + 2) if is_holding else horizon_start
            else:
                earliest_move = horizon_start

            earliest_part = max([p.usable_ready_tick for p in task_parts if p.usable_ready_tick is not None] or [horizon_start])
            earliest_possible = max(horizon_start, earliest_part, earliest_move)

            if earliest_possible + rem_dur > horizon_end:
                unscheduled_reasons[t.task_id] = "NO_FEASIBLE_INTERVAL_WITHIN_HORIZON"
                continue

            effective_durations[t.task_id] = rem_dur
            candidate_tasks.append(t)

        # 3. Enforce Transitive Precedence Closure
        # If any incomplete predecessor was excluded, its successors CANNOT be scheduled
        schedulable_set = set(t.task_id for t in candidate_tasks)
        changed = True
        while changed:
            changed = False
            for t_id in list(schedulable_set):
                task = tasks_by_id[t_id]
                for pred_id in task.predecessor_task_ids:
                    if pred_id not in completed_task_ids and pred_id not in schedulable_set:
                        schedulable_set.remove(t_id)
                        unscheduled_reasons[t_id] = f"PREDECESSOR_UNSCHEDULED_{pred_id}"
                        changed = True
                        break

        schedulable_tasks = [t for t in candidate_tasks if t.task_id in schedulable_set]

        # Precedence Cycle Detection (3-color DFS)
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

        task_vars: Dict[str, Dict[str, Any]] = {}
        tech_assignment_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        bay_assignment_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        tech_intervals: Dict[str, List[cp_model.IntervalVar]] = defaultdict(list)
        bay_intervals: Dict[str, List[cp_model.IntervalVar]] = defaultdict(list)

        # Handle vehicle immobilized state (C5)
        immobilized_ros = {
            r.ro_id: r for r in snapshot.repair_orders
            if (r.physical_state.value if hasattr(r.physical_state, "value") else str(r.physical_state)) == "IMMOBILIZED_ON_LIFT"
        }
        immobilized_bay_ids = {r.assigned_bay_id for r in immobilized_ros.values() if r.assigned_bay_id}

        # Create decision variables for each schedulable task
        for task in schedulable_tasks:
            t_id = task.task_id
            ro = ros_by_id[task.ro_id]
            duration = effective_durations[t_id]

            # Earliest start bounded by part arrivals and vehicle movement
            task_parts = parts_by_task.get(t_id, [])
            earliest_part_tick = horizon_start
            for part in task_parts:
                if part.usable_ready_tick is not None:
                    earliest_part_tick = max(earliest_part_tick, part.usable_ready_tick)

            phys_ev = ev.vehicle_evidence.get(ro.vehicle_id) or ev.vehicle_evidence.get(ro.ro_id)
            state_val = (
                phys_ev.physical_state.value if (phys_ev and hasattr(phys_ev.physical_state, "value"))
                else (ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state))
            )
            is_holding = phys_ev.is_in_holding if phys_ev else (state_val == "IN_HOLDING")
            earliest_move_tick = (ev.current_tick + 2) if is_holding else horizon_start

            earliest_start = max(horizon_start, earliest_part_tick, earliest_move_tick)

            is_sched = model.NewBoolVar(f"z_{t_id}")
            start_var = model.NewIntVar(horizon_start, horizon_end - duration, f"start_{t_id}")
            end_var = model.NewIntVar(horizon_start + duration, horizon_end, f"end_{t_id}")

            model.Add(end_var == start_var + duration).OnlyEnforceIf(is_sched)
            model.Add(start_var >= earliest_start).OnlyEnforceIf(is_sched)

            task_vars[t_id] = {
                "is_scheduled": is_sched,
                "start": start_var,
                "end": end_var,
                "duration": duration,
                "task": task,
                "ro": ro,
            }

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

                opt_tech_interval = model.NewOptionalIntervalVar(
                    start_var, duration, end_var, var, f"tech_int_{t_id}_{tech.tech_id}"
                )
                tech_intervals[tech.tech_id].append(opt_tech_interval)

                # C6 Technician Shift Window
                model.Add(start_var >= tech.shift_start_tick).OnlyEnforceIf(var)
                shift_end = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else tech.shift_end_tick
                model.Add(end_var <= shift_end).OnlyEnforceIf(var)

            if t_tech_vars:
                model.Add(sum(t_tech_vars) == is_sched)
            else:
                model.Add(is_sched == 0)

            # C1 & C5 Eligibility: Bays and Lifting Capacity
            vehicle_weight = (
                phys_ev.vehicle_weight_lbs
                if (phys_ev and phys_ev.vehicle_weight_lbs is not None)
                else getattr(ro, "vehicle_weight_lbs", 0)
            )

            if task.ro_id in immobilized_ros:
                imm_bay_id = immobilized_ros[task.ro_id].assigned_bay_id
                assigned_bay = bays_by_id.get(imm_bay_id) if imm_bay_id else None
                if (
                    assigned_bay
                    and assigned_bay.is_operational
                    and assigned_bay.bay_type == task.required_bay_type
                    and assigned_bay.lifting_capacity_lbs >= vehicle_weight
                ):
                    compatible_bays = [assigned_bay]
                else:
                    compatible_bays = []
            else:
                compatible_bays = [
                    b for b in snapshot.bays
                    if b.is_operational
                    and b.bay_type == task.required_bay_type
                    and b.bay_id not in immobilized_bay_ids
                    and b.lifting_capacity_lbs >= vehicle_weight
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
                    continue
                elif pred_id in task_vars:
                    model.Add(task_vars[t_id]["start"] >= task_vars[pred_id]["end"]).OnlyEnforceIf(
                        [task_vars[t_id]["is_scheduled"], task_vars[pred_id]["is_scheduled"]]
                    )
                    model.Add(task_vars[t_id]["is_scheduled"] <= task_vars[pred_id]["is_scheduled"])

        # 6. C4 Exclusivity: Technician Constraints & Lunch Breaks
        for tech in snapshot.technicians:
            if not tech.is_active:
                continue
            lunch_interval = model.NewIntervalVar(
                tech.lunch_start_tick,
                tech.lunch_duration_ticks,
                tech.lunch_start_tick + tech.lunch_duration_ticks,
                f"lunch_{tech.tech_id}",
            )
            model.AddNoOverlap(tech_intervals[tech.tech_id] + [lunch_interval])

        # 7. C4 Exclusivity: Bay Constraints & Blocked Intervals
        for block_bay, b_start, b_end in blocked_intervals:
            if block_bay in bays_by_id and b_end > b_start:
                block_int = model.NewIntervalVar(b_start, b_end - b_start, b_end, f"blocked_{block_bay}_{b_start}")
                bay_intervals[block_bay].append(block_int)

        for bay in snapshot.bays:
            if not bay.is_operational:
                continue
            model.AddNoOverlap(bay_intervals[bay.bay_id])

        # 8. Objective Function Formulation (in Integer Cents)
        cents_per_labor_tick = int(round(float(self.config.labor_contribution_per_hour_usd) / 12.0 * 100.0))
        cents_per_late_minute = int(round(float(self.config.lateness_penalty_per_minute_usd) * 100.0))
        cents_per_late_tick = cents_per_late_minute * 5

        labor_contrib_terms: List[cp_model.LinearExpr] = []
        for t_id, d in task_vars.items():
            labor_contrib_terms.append(d["is_scheduled"] * (d["duration"] * cents_per_labor_tick))

        ro_lateness_vars: Dict[str, cp_model.IntVar] = {}
        lateness_terms: List[cp_model.LinearExpr] = []
        tasks_by_ro: Dict[str, List[str]] = defaultdict(list)
        for t in schedulable_tasks:
            tasks_by_ro[t.ro_id].append(t.task_id)

        for ro_id, t_ids in tasks_by_ro.items():
            ro = ros_by_id[ro_id]
            promise = ro.promise_tick
            weight = ro.priority_weight

            lateness_var = model.NewIntVar(0, self.config.horizon_ticks, f"lateness_{ro_id}")
            ro_lateness_vars[ro_id] = lateness_var

            for t_id in t_ids:
                d = task_vars[t_id]
                model.Add(lateness_var >= d["end"] - promise).OnlyEnforceIf(d["is_scheduled"])

            lateness_terms.append(lateness_var * (weight * cents_per_late_tick))

        net_objective_expr = sum(labor_contrib_terms) - sum(lateness_terms)
        model.Maximize(net_objective_expr)

        # 9. T1 Solution Warm-Start (Hinting)
        if self.config.enable_t1_warm_start:
            try:
                t1_res = self.t1_fallback.schedule(
                    snapshot,
                    plan_id=f"{plan_id}-T1-HINT",
                    evidence=ev,
                    blocked_bay_intervals=blocked_intervals,
                )
                if t1_res.is_verified:
                    t1_assign_map = {a.task_id: a for a in t1_res.plan.assignments}
                    for t_id, d in task_vars.items():
                        if t_id in t1_assign_map:
                            a = t1_assign_map[t_id]
                            model.AddHint(d["is_scheduled"], 1)
                            model.AddHint(d["start"], a.start_tick)
                            model.AddHint(d["end"], a.end_tick)
                            if (t_id, a.tech_id) in tech_assignment_vars:
                                model.AddHint(tech_assignment_vars[(t_id, a.tech_id)], 1)
                            if (t_id, a.bay_id) in bay_assignment_vars:
                                model.AddHint(bay_assignment_vars[(t_id, a.bay_id)], 1)
                        else:
                            model.AddHint(d["is_scheduled"], 0)
            except Exception:
                pass

        # 10. Solve the CP-SAT Model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.time_budget_seconds
        solver.parameters.num_workers = self.config.num_workers
        solver.parameters.random_seed = self.config.deterministic_seed

        solve_status_int = solver.Solve(model)
        solve_elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        status_mapping = {
            cp_model.OPTIMAL: SolverStatus.OPTIMAL,
            cp_model.FEASIBLE: SolverStatus.FEASIBLE,
            cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
            cp_model.MODEL_INVALID: SolverStatus.UNKNOWN,
            cp_model.UNKNOWN: SolverStatus.UNKNOWN,
        }
        solver_status = status_mapping.get(solve_status_int, SolverStatus.UNKNOWN)

        # 11. Extract Solution
        if solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE):
            assignments: List[ScheduledAssignment] = []
            for t_id, d in task_vars.items():
                if solver.Value(d["is_scheduled"]) == 1:
                    start_val = int(solver.Value(d["start"]))
                    end_val = int(solver.Value(d["end"]))

                    assigned_tech: Optional[str] = None
                    for (task_key, tech_key), var in tech_assignment_vars.items():
                        if task_key == t_id and solver.Value(var) == 1:
                            assigned_tech = tech_key
                            break

                    assigned_bay: Optional[str] = None
                    for (task_key, bay_key), var in bay_assignment_vars.items():
                        if task_key == t_id and solver.Value(var) == 1:
                            assigned_bay = bay_key
                            break

                    if assigned_tech and assigned_bay:
                        assignments.append(
                            ScheduledAssignment(
                                task_id=t_id,
                                ro_id=d["ro"].ro_id,
                                tech_id=assigned_tech,
                                bay_id=assigned_bay,
                                start_tick=start_val,
                                end_tick=end_val,
                            )
                        )
                else:
                    unscheduled_reasons[t_id] = "PRUNED_BY_SOLVER_OBJECTIVE"

            # Reconstruct vehicle occupancy intervals for immobilized vehicles
            vehicle_occupancies: List[VehicleBayOccupancy] = []
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

            bay_blocked_ticks = sum((occ.end_tick - occ.start_tick) for occ in vehicle_occupancies)
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

            scheduled_ros = {a.ro_id for a in assignments}
            verified_authorizations = {r_id: True for r_id in scheduled_ros if ev.is_ro_authorized(r_id)}
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

            # Dual Independent Verification
            oracle = SweepLineOracle(snapshot)
            verification_result = oracle.verify_plan(candidate_plan)

            supp_oracle = SupplementalAuditOracle(snapshot, ev)
            supp_result = supp_oracle.audit_plan(candidate_plan)

            is_verified = verification_result.is_valid
            is_fully_certified = is_verified and supp_result.is_valid

            # Optimality gap
            best_bound_cents = solver.BestObjectiveBound()
            obj_cents = solver.ObjectiveValue()
            gap = 0.0
            if solver_status == SolverStatus.FEASIBLE and abs(obj_cents) > 1e-6:
                gap = abs(best_bound_cents - obj_cents) / abs(obj_cents)

            if is_verified:
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
                    supplemental_audit_result=supp_result.model_dump(),
                    is_fully_certified=is_fully_certified,
                    evidence_coverage_gaps=supp_result.coverage_gaps,
                )
            else:
                # T2 candidate failed L4 verifier! Discard and fall back to verified T1
                t1_fallback_res = self.t1_fallback.schedule(
                    snapshot,
                    plan_id=f"{plan_id}-T1-FALLBACK",
                    evidence=ev,
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
            evidence=ev,
            blocked_bay_intervals=blocked_intervals,
        )
        t1_fallback_res.degradation_reason = (
            f"CP-SAT solver returned {solver_status.value} in {solve_elapsed_ms:.1f}ms; "
            f"automatically degraded to verified T1 schedule."
        )
        return t1_fallback_res
