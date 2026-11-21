"""Discrete OR-Tools CP-SAT Interval Scheduler for ServiceYield AI Optimise Engine.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 3: Optimise)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.3)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md (A3: $120/hr sold labor, nu = $2.00/min = $120/hr)
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md (Task 1.4)

Mathematical Formulation:
Variables:
- x_i in [horizon_start, horizon_end - d_i]: Start tick of task i
- u_i in [horizon_start + d_i, horizon_end]: End tick of task i
- z_i in {0, 1}: Task execution indicator (1 if scheduled, 0 if unscheduled)
- y_{i, k} in {0, 1}: Assignment indicator of task i to eligible technician k
- a_{i, b} in {0, 1}: Assignment indicator of task i to compatible bay b
- I_{i, k} = NewOptionalIntervalVar(x_i, d_i, u_i, y_{i, k}): Technician optional interval
- I_{i, b} = NewOptionalIntervalVar(x_i, d_i, u_i, a_{i, b}): Bay optional interval

Objective:
Maximize Net Economic Yield Z = Labor Gross Contribution - Weighted Customer Lateness Penalty - Bay Blocked Idle Penalty
Scaled to integer cents:
max Z_cents = sum_i(1000 * d_i * z_i) - sum_r(250 * w_r * Lateness_r) - sum_occ(50 * IdleTicks_occ)

Inviolable Verification Gate:
Every solution (optimal or feasible) must pass the independent L4 Sweep-Line Oracle
AND the Supplemental Audit Oracle. If dual verification fails, the engine falls back to T1.
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


class CPSATScheduler:
    """Production T2 Discrete CP-SAT Scheduler with warm-starting and dual verification."""

    def __init__(self, config: Optional[OptimiseConfig] = None):
        self.config = config or OptimiseConfig()
        self.t1_fallback = T1BitsetScheduler(self.config)

    def schedule(
        self,
        snapshot: DealershipSnapshotSchema,
        plan_id: str = "PLAN-T2-OPTIMISE",
        evidence: Optional[WorkshopEvidenceBundle] = None,
        blocked_bay_intervals: Optional[List[Tuple[str, int, int]]] = None,
        warm_start_result: Optional[ScheduleResult] = None,
    ) -> ScheduleResult:
        """Solves the discrete workshop scheduling problem using OR-Tools CP-SAT."""
        start_time = time.perf_counter()
        ev = evidence or WorkshopEvidenceBundle(current_tick=snapshot.rooftop.operating_day_start_tick)
        blocked_intervals = blocked_bay_intervals or []

        horizon_start = self.config.horizon_start_tick
        horizon_end = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else self.config.horizon_end_tick

        # 1. State Lookups
        bays_by_id = {b.bay_id: b for b in snapshot.bays}
        techs_by_id = {t.tech_id: t for t in snapshot.technicians}
        ros_by_id = {r.ro_id: r for r in snapshot.repair_orders}
        tasks_by_id = {t.task_id: t for t in snapshot.tasks}

        parts_by_task: Dict[str, List[Any]] = defaultdict(list)
        for p in snapshot.part_requirements:
            parts_by_task[p.task_id].append(p)

        # 2. Filter Candidate Incomplete Tasks
        candidate_tasks: List[TaskSchema] = []
        completed_task_ids: Set[str] = set()
        unscheduled_reasons: Dict[str, str] = {}
        effective_durations: Dict[str, int] = {}

        # Handle Immobilized Vehicles
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
                unscheduled_reasons[f"RO_{r_id}"] = f"CONFLICTING_IMMOBILIZED_BAY_OCCUPANCY_{target_bay}"
            else:
                immobilized_bay_reservations[r_id] = target_bay
                bay_to_imm_ro[target_bay] = r_id

        immobilized_bay_ids = set(immobilized_bay_reservations.values())

        for t in snapshot.tasks:
            status_str = t.status.value if hasattr(t.status, "value") else str(t.status)
            if status_str == "COMPLETED":
                completed_task_ids.add(t.task_id)
                continue

            # C7 Customer Estimate Authorization Gate
            if not ev.is_ro_authorized(t.ro_id):
                unscheduled_reasons[t.task_id] = f"UNAUTHORIZED_CUSTOMER_ESTIMATE_{t.ro_id}"
                continue

            # C1 Fitment and Vehicle Weight Gates (Finding A2 & A3)
            ro = ros_by_id.get(t.ro_id)
            if not ro:
                unscheduled_reasons[t.task_id] = "RO_NOT_FOUND"
                continue

            phys_ev = ev.get_vehicle_physical_evidence(ro.vehicle_id, ro.ro_id)
            if phys_ev is None:
                unscheduled_reasons[t.task_id] = f"MISSING_VEHICLE_EVIDENCE_{ro.vehicle_id}"
                continue

            if phys_ev.fitment_verified is None:
                unscheduled_reasons[t.task_id] = f"UNVERIFIED_PARTS_FITMENT_{ro.vehicle_id}"
                continue
            elif phys_ev.fitment_verified is False:
                unscheduled_reasons[t.task_id] = f"REJECTED_PARTS_FITMENT_{ro.vehicle_id}"
                continue

            if phys_ev.vehicle_weight_lbs is None:
                unscheduled_reasons[t.task_id] = f"MISSING_VEHICLE_WEIGHT_EVIDENCE_{ro.vehicle_id}"
                continue

            # C5 Vehicle Physical State Gate
            state_val = (
                phys_ev.physical_state.value if hasattr(phys_ev.physical_state, "value")
                else (ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state))
            )
            if state_val == "UNKNOWN":
                unscheduled_reasons[t.task_id] = f"UNKNOWN_VEHICLE_STATE_{ro.ro_id}"
                continue

            if state_val == "IMMOBILIZED_ON_LIFT":
                if ro.ro_id in imm_missing_bays:
                    unscheduled_reasons[t.task_id] = f"IMMOBILIZED_VEHICLE_MISSING_ASSIGNED_BAY_{ro.ro_id}"
                    continue

            # Task Execution Progress and Remaining Duration Evidence (Finding B1)
            status_val = t.status.value if hasattr(t.status, "value") else str(t.status)
            if status_val in ("IN_PROGRESS", "STALLED"):
                prog = ev.task_progress.get(t.task_id)
                if not prog:
                    unscheduled_reasons[t.task_id] = f"MISSING_EXECUTION_PROGRESS_{t.task_id}"
                    continue
                if prog.remaining_duration_ticks is None or prog.remaining_duration_ticks <= 0:
                    unscheduled_reasons[t.task_id] = f"MISSING_EXECUTION_PROGRESS_REMAINING_DURATION_{t.task_id}"
                    continue
                if prog.requires_existing_assignment and (not prog.existing_bay_id or not prog.existing_tech_id):
                    unscheduled_reasons[t.task_id] = f"MISSING_EXISTING_ASSIGNMENT_EVIDENCE_{t.task_id}"
                    continue
                rem_dur = prog.remaining_duration_ticks
            else:
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

            is_holding = phys_ev.is_in_holding if phys_ev else (state_val == "IN_HOLDING")
            if is_holding and not ev.available_porter_tech_ids:
                unscheduled_reasons[t.task_id] = f"NO_PORTER_OR_TECH_AVAILABLE_FOR_MOVE_{ro.ro_id}"
                continue

            earliest_move = (ev.current_tick + 2) if is_holding else horizon_start
            earliest_part = max([p.usable_ready_tick for p in task_parts if p.usable_ready_tick is not None] or [horizon_start])
            earliest_possible = max(ev.current_tick, horizon_start, earliest_part, earliest_move)

            if earliest_possible + rem_dur > horizon_end:
                unscheduled_reasons[t.task_id] = "NO_FEASIBLE_INTERVAL_WITHIN_HORIZON"
                continue

            effective_durations[t.task_id] = rem_dur
            candidate_tasks.append(t)

        # 3. Enforce Transitive Precedence Closure
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
        porter_intervals: Dict[str, List[cp_model.IntervalVar]] = defaultdict(list)
        move_vars: Dict[str, Dict[str, Any]] = {}

        # Pre-allocate existing WIP active intervals into tech_intervals and bay_intervals (Finding B1)
        for task in snapshot.tasks:
            status_val = task.status.value if hasattr(task.status, "value") else str(task.status)
            if status_val in ("IN_PROGRESS", "STALLED"):
                prog = ev.task_progress.get(task.task_id)
                if prog and prog.occupied_start_tick is not None:
                    occ_end = prog.occupied_end_tick if prog.occupied_end_tick is not None else ev.current_tick
                    if occ_end > prog.occupied_start_tick:
                        occ_dur = occ_end - prog.occupied_start_tick
                        if prog.existing_tech_id:
                            tech_intervals[prog.existing_tech_id].append(
                                model.NewIntervalVar(prog.occupied_start_tick, occ_dur, occ_end, f"wip_tech_{task.task_id}")
                            )
                        if prog.existing_bay_id:
                            bay_intervals[prog.existing_bay_id].append(
                                model.NewIntervalVar(prog.occupied_start_tick, occ_dur, occ_end, f"wip_bay_{task.task_id}")
                            )

        # Identify holding entry tasks requiring explicit movement operations
        holding_entry_tasks: Dict[str, Any] = {}
        for ro in snapshot.repair_orders:
            phys_ev = ev.get_vehicle_physical_evidence(ro.vehicle_id, ro.ro_id)
            state_val = (
                phys_ev.physical_state.value if (phys_ev and hasattr(phys_ev.physical_state, "value"))
                else (ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state))
            )
            is_holding = phys_ev.is_in_holding if phys_ev else (state_val == "IN_HOLDING")
            if is_holding:
                ro_tasks = [t for t in schedulable_tasks if t.ro_id == ro.ro_id]
                ro_tasks.sort(key=lambda t: (t.sequence_order, t.task_id))
                entry_candidates = [
                    t for t in ro_tasks
                    if not any(p in set(x.task_id for x in ro_tasks) for p in t.predecessor_task_ids)
                ]
                if entry_candidates:
                    holding_entry_tasks[entry_candidates[0].task_id] = ro

        # Decision Variables & Intervals for Schedulable Tasks
        for task in schedulable_tasks:
            t_id = task.task_id
            duration = effective_durations[t_id]
            ro = ros_by_id[task.ro_id]
            phys_ev = ev.get_vehicle_physical_evidence(ro.vehicle_id, ro.ro_id)

            # C2 Earliest Part Readiness
            task_parts = parts_by_task.get(t_id, [])
            earliest_part_tick = max([p.usable_ready_tick for p in task_parts if p.usable_ready_tick is not None] or [horizon_start])

            # C5 Vehicle Physical State & Holding Move
            state_val = (
                phys_ev.physical_state.value if (phys_ev and hasattr(phys_ev.physical_state, "value"))
                else (ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state))
            )
            is_entry_holding = t_id in holding_entry_tasks
            earliest_move_tick = (ev.current_tick + 2) if is_entry_holding else horizon_start
            earliest_start = max(ev.current_tick, horizon_start, earliest_part_tick, earliest_move_tick)

            is_sched = model.NewBoolVar(f"z_{t_id}")
            start_var = model.NewIntVar(horizon_start, horizon_end - duration, f"start_{t_id}")
            end_var = model.NewIntVar(horizon_start + duration, horizon_end, f"end_{t_id}")

            model.Add(end_var == start_var + duration).OnlyEnforceIf(is_sched)
            model.Add(start_var >= earliest_start).OnlyEnforceIf(is_sched)

            if is_entry_holding:
                # Explicit CP-SAT 2-tick movement interval
                move_start = model.NewIntVar(ev.current_tick, horizon_end - 2, f"move_start_{t_id}")
                move_end = model.NewIntVar(ev.current_tick + 2, horizon_end, f"move_end_{t_id}")
                model.Add(move_end == move_start + 2).OnlyEnforceIf(is_sched)
                model.Add(start_var >= move_end).OnlyEnforceIf(is_sched)

                m_res_vars: Dict[str, cp_model.IntVar] = {}
                for p_id in sorted(ev.available_porter_tech_ids):
                    res_var = model.NewBoolVar(f"move_res_{t_id}_{p_id}")
                    m_res_vars[p_id] = res_var
                    opt_m_int = model.NewOptionalIntervalVar(move_start, 2, move_end, res_var, f"move_int_{t_id}_{p_id}")
                    if p_id in techs_by_id:
                        tech_intervals[p_id].append(opt_m_int)
                    else:
                        porter_intervals[p_id].append(opt_m_int)

                if m_res_vars:
                    model.Add(sum(m_res_vars.values()) == is_sched)
                else:
                    model.Add(is_sched == 0)

                move_vars[t_id] = {
                    "start": move_start,
                    "end": move_end,
                    "res_vars": m_res_vars,
                    "ro": ro,
                }

            task_vars[t_id] = {
                "is_scheduled": is_sched,
                "start": start_var,
                "end": end_var,
                "duration": duration,
                "task": task,
                "ro": ro,
            }

            # WIP Locked Assignments (Finding B1)
            prog = ev.task_progress.get(t_id)
            locked_bay_id = prog.existing_bay_id if (prog and prog.is_assignment_locked) else None
            locked_tech_id = prog.existing_tech_id if (prog and prog.is_assignment_locked) else None

            # C1 Eligibility: Technicians
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
            vehicle_weight = phys_ev.vehicle_weight_lbs if phys_ev else 3800

            if task.ro_id in immobilized_ros:
                imm_bay_id = immobilized_bay_reservations.get(task.ro_id)
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
            elif locked_bay_id:
                assigned_bay = bays_by_id.get(locked_bay_id)
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

        # 5. Global Resource Exclusivity Constraints (C4)
        for tech in snapshot.technicians:
            lunch_interval = model.NewIntervalVar(
                tech.lunch_start_tick, tech.lunch_duration_ticks,
                tech.lunch_start_tick + tech.lunch_duration_ticks, f"lunch_{tech.tech_id}"
            )
            intervals = tech_intervals[tech.tech_id] + [lunch_interval]
            model.AddNoOverlap(intervals)

        for bay in snapshot.bays:
            blocked_for_bay: List[cp_model.IntervalVar] = []
            if not bay.is_operational:
                blocked_for_bay.append(
                    model.NewIntervalVar(0, self.config.horizon_ticks, self.config.horizon_ticks, f"inop_{bay.bay_id}")
                )
            for b_id, b_start, b_end in blocked_intervals:
                if b_id == bay.bay_id and b_end > b_start:
                    blocked_for_bay.append(
                        model.NewIntervalVar(b_start, b_end - b_start, b_end, f"blocked_{bay.bay_id}_{b_start}")
                    )

            intervals = bay_intervals[bay.bay_id] + blocked_for_bay
            model.AddNoOverlap(intervals)

        # Porter Exclusivity Constraints (Non-technician porters)
        for p_id, p_ints in porter_intervals.items():
            model.AddNoOverlap(p_ints)

        # Immobilized Vehicle Bay Exclusivity (C4 & C5)
        # An immobilized vehicle physically occupies its bay until its repair completes.
        # Any other vehicle assigned to that bay can only enter after the immobilized repair finishes.
        # If the immobilized vehicle's repair is not scheduled, no other vehicle can use the bay.
        for imm_ro_id, assigned_bay in immobilized_bay_reservations.items():
            imm_tasks = [t for t in schedulable_tasks if t.ro_id == imm_ro_id]
            if not imm_tasks:
                for other_t in schedulable_tasks:
                    if other_t.ro_id != imm_ro_id and (other_t.task_id, assigned_bay) in bay_assignment_vars:
                        model.Add(bay_assignment_vars[(other_t.task_id, assigned_bay)] == 0)
                continue

            t_imm = imm_tasks[0]
            imm_is_sched = task_vars[t_imm.task_id]["is_scheduled"]
            imm_end = task_vars[t_imm.task_id]["end"]

            for other_t in schedulable_tasks:
                if other_t.ro_id != imm_ro_id and (other_t.task_id, assigned_bay) in bay_assignment_vars:
                    other_on_bay = bay_assignment_vars[(other_t.task_id, assigned_bay)]
                    model.Add(other_on_bay <= imm_is_sched)
                    min_gap = 2 if other_t.task_id in move_vars else 0
                    model.Add(task_vars[other_t.task_id]["start"] >= imm_end + min_gap).OnlyEnforceIf(other_on_bay)

        # 6. Precedence DAG Constraints (C3)
        for task in schedulable_tasks:
            t_id = task.task_id
            for pred_id in task.predecessor_task_ids:
                if pred_id in task_vars:
                    succ_sched = task_vars[t_id]["is_scheduled"]
                    pred_sched = task_vars[pred_id]["is_scheduled"]
                    model.Add(succ_sched <= pred_sched)
                    model.Add(task_vars[t_id]["start"] >= task_vars[pred_id]["end"]).OnlyEnforceIf(succ_sched)

        # 7. Customer Promise Lateness Formulation (Objective)
        ro_tasks_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for t_info in task_vars.values():
            ro_tasks_map[t_info["ro"].ro_id].append(t_info)

        ro_lateness_vars: Dict[str, cp_model.IntVar] = {}
        for ro_id, t_infos in ro_tasks_map.items():
            ro = ros_by_id[ro_id]
            promise = ro.promise_tick
            max_lat = max(0, horizon_end - promise)
            lat_var = model.NewIntVar(0, max_lat, f"lateness_{ro_id}")
            ro_lateness_vars[ro_id] = lat_var

            for t_info in t_infos:
                is_sc = t_info["is_scheduled"]
                end_v = t_info["end"]
                model.Add(lat_var >= end_v - promise).OnlyEnforceIf(is_sc)

        # 8. Economic Objective Function Formulation
        gross_cents_per_tick = int(round(self.config.labor_contribution_per_hour_usd / Decimal("12") * Decimal("100")))
        late_cents_per_tick = int(round(self.config.lateness_penalty_per_minute_usd * Decimal("500")))
        blocked_cents_per_tick = int(round(self.config.blocked_bay_penalty_per_minute_usd * Decimal("500")))
        churn_cents_per_reassignment = int(round(self.config.churn_penalty_per_move_usd * Decimal("100")))

        objective_terms = []
        for t_id, t_info in task_vars.items():
            dur = t_info["duration"]
            is_sc = t_info["is_scheduled"]
            objective_terms.append(gross_cents_per_tick * dur * is_sc)

        for ro_id, lat_var in ro_lateness_vars.items():
            ro = ros_by_id[ro_id]
            weight = ro.priority_weight
            objective_terms.append(-late_cents_per_tick * weight * lat_var)

        # Bay Blocked Idle Opportunity Cost Formulation
        blocked_penalty_terms = []
        if blocked_cents_per_tick > 0:
            for imm_ro_id in immobilized_ros:
                imm_tasks = [t_info for t_info in task_vars.values() if t_info["ro"].ro_id == imm_ro_id]
                if imm_tasks:
                    phys_ev = ev.get_vehicle_physical_evidence(ros_by_id[imm_ro_id].vehicle_id, imm_ro_id)
                    occ_start = phys_ev.occupancy_start_tick if (phys_ev and phys_ev.occupancy_start_tick is not None) else ev.current_tick
                    for t_info in imm_tasks:
                        # start - occ_start represents idle blocked ticks before repair commencement
                        blocked_penalty_terms.append(blocked_cents_per_tick * (t_info["start"] - occ_start))

        for term in blocked_penalty_terms:
            objective_terms.append(-term)

        # Schedule Churn / Disruption Penalty Formulation
        churn_vars = []
        if churn_cents_per_reassignment > 0:
            for t_id, prog in ev.task_progress.items():
                if t_id in task_vars:
                    if prog.existing_tech_id:
                        for (task_k, tech_k), var in tech_assignment_vars.items():
                            if task_k == t_id and tech_k != prog.existing_tech_id:
                                churn_vars.append(var)
                    if prog.existing_bay_id:
                        for (task_b, bay_b), var in bay_assignment_vars.items():
                            if task_b == t_id and bay_b != prog.existing_bay_id:
                                churn_vars.append(var)

        for var in churn_vars:
            objective_terms.append(-churn_cents_per_reassignment * var)

        model.Maximize(sum(objective_terms))

        # 9. T1 Warm-Start Hint Injection
        if warm_start_result is None:
            warm_start_result = self.t1_fallback.schedule(
                snapshot, plan_id=f"{plan_id}-HINT", evidence=ev, blocked_bay_intervals=blocked_intervals
            )

        if warm_start_result and warm_start_result.plan:
            for assignment in warm_start_result.plan.assignments:
                t_id = assignment.task_id
                if t_id in task_vars:
                    model.AddHint(task_vars[t_id]["is_scheduled"], 1)
                    model.AddHint(task_vars[t_id]["start"], assignment.start_tick)
                    model.AddHint(task_vars[t_id]["end"], assignment.end_tick)
                    if (t_id, assignment.tech_id) in tech_assignment_vars:
                        model.AddHint(tech_assignment_vars[(t_id, assignment.tech_id)], 1)
                    if (t_id, assignment.bay_id) in bay_assignment_vars:
                        model.AddHint(bay_assignment_vars[(t_id, assignment.bay_id)], 1)
            for pm in getattr(warm_start_result, "planned_movements", []):
                t_id = pm.related_task_id
                if t_id in move_vars:
                    mv = move_vars[t_id]
                    model.AddHint(mv["start"], pm.start_tick)
                    model.AddHint(mv["end"], pm.end_tick)
                    if pm.assigned_resource_id in mv["res_vars"]:
                        model.AddHint(mv["res_vars"][pm.assigned_resource_id], 1)

        # 10. Execute CP-SAT Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.time_budget_seconds
        solver.parameters.num_workers = self.config.num_workers
        solver.parameters.random_seed = getattr(self.config, "deterministic_seed", 42)

        solve_start = time.perf_counter()
        raw_status = solver.Solve(model)
        solve_elapsed_ms = (time.perf_counter() - solve_start) * 1000.0

        status_map = {
            cp_model.OPTIMAL: SolverStatus.OPTIMAL,
            cp_model.FEASIBLE: SolverStatus.FEASIBLE,
            cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
            cp_model.MODEL_INVALID: SolverStatus.UNKNOWN,
            cp_model.UNKNOWN: SolverStatus.UNKNOWN,
        }
        solver_status = status_map.get(raw_status, SolverStatus.UNKNOWN)

        # 11. Extract Candidate Solution & Assembly
        if solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE):
            assignments = []
            for t_id, t_info in task_vars.items():
                if solver.Value(t_info["is_scheduled"]) == 1:
                    start_tick = int(solver.Value(t_info["start"]))
                    end_tick = int(solver.Value(t_info["end"]))
                    assigned_tech = None
                    for (task_k, tech_k), var in tech_assignment_vars.items():
                        if task_k == t_id and solver.Value(var) == 1:
                            assigned_tech = tech_k
                            break

                    assigned_bay = None
                    for (task_b, bay_b), var in bay_assignment_vars.items():
                        if task_b == t_id and solver.Value(var) == 1:
                            assigned_bay = bay_b
                            break

                    if assigned_tech and assigned_bay:
                        assignments.append(
                            ScheduledAssignment(
                                task_id=t_id,
                                ro_id=t_info["ro"].ro_id,
                                tech_id=assigned_tech,
                                bay_id=assigned_bay,
                                start_tick=start_tick,
                                end_tick=end_tick,
                            )
                        )
                else:
                    unscheduled_reasons[t_id] = "PRUNED_BY_SOLVER_OBJECTIVE"

            # Extract Planned Vehicle Movements for Holding Tasks
            planned_movements: List[PlannedVehicleMovement] = []
            for t_id, mv in move_vars.items():
                if solver.Value(task_vars[t_id]["is_scheduled"]) == 1:
                    m_s = int(solver.Value(mv["start"]))
                    m_e = int(solver.Value(mv["end"]))
                    assigned_res = None
                    for r_id, r_var in mv["res_vars"].items():
                        if solver.Value(r_var) == 1:
                            assigned_res = r_id
                            break
                    assigned_bay = None
                    for (task_b, bay_b), var in bay_assignment_vars.items():
                        if task_b == t_id and solver.Value(var) == 1:
                            assigned_bay = bay_b
                            break
                    if assigned_res and assigned_bay:
                        m_ro = mv["ro"]
                        planned_movements.append(
                            PlannedVehicleMovement(
                                vehicle_id=m_ro.vehicle_id,
                                ro_id=m_ro.ro_id,
                                origin_location="HOLDING_LOT",
                                target_bay_id=assigned_bay,
                                start_tick=m_s,
                                end_tick=m_e,
                                assigned_resource_id=assigned_res,
                                resource_type="TECHNICIAN" if assigned_res in techs_by_id else "PORTER",
                                resource_availability="AVAILABLE",
                                movement_status="PLANNED",
                                related_task_id=t_id,
                            )
                        )

            # Vehicle Occupancy for Immobilized Vehicles
            vehicle_occupancies = []
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

            # Calculate metrics using exact integer cents matching CP-SAT formulation
            solver_obj_cents = int(round(solver.ObjectiveValue()))
            solver_obj_usd = (Decimal(str(solver_obj_cents)) / Decimal("100")).quantize(Decimal("0.01"))
            best_bound_cents = int(round(solver.BestObjectiveBound()))
            best_bound_usd = (Decimal(str(best_bound_cents)) / Decimal("100")).quantize(Decimal("0.01"))

            total_labor_ticks = sum(a.end_tick - a.start_tick for a in assignments)
            gross_cents = total_labor_ticks * gross_cents_per_tick
            gross_contrib = Decimal(str(gross_cents)) / Decimal("100")

            # RO Completion Analysis
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

            late_cents = weighted_lateness_ticks * late_cents_per_tick
            lateness_penalty = Decimal(str(late_cents)) / Decimal("100")
            bay_blocked_ticks = sum((occ.end_tick - occ.start_tick) for occ in vehicle_occupancies)
            bay_blocked_penalty = (Decimal(str(bay_blocked_ticks * blocked_cents_per_tick)) / Decimal("100")).quantize(Decimal("0.01"))

            churn_score = sum(int(solver.Value(v)) for v in churn_vars) if churn_vars else None
            churn_penalty = (Decimal(str(churn_score * churn_cents_per_reassignment)) / Decimal("100")).quantize(Decimal("0.01")) if churn_score is not None else None
            churn_status = "AVAILABLE" if churn_score is not None else "NOT_APPLICABLE"

            configured_terms = ["gross_contribution", "lateness_penalty"]
            unconfigured_terms = ["sourcing_cost"]
            if blocked_cents_per_tick > 0:
                configured_terms.append("bay_blocked_penalty")
            else:
                unconfigured_terms.append("bay_blocked_penalty")
            if churn_cents_per_reassignment > 0:
                configured_terms.append("schedule_churn_penalty")
            else:
                unconfigured_terms.append("schedule_churn_penalty")

            metrics = ObjectiveMetrics(
                gross_contribution_usd=gross_contrib.quantize(Decimal("0.01")),
                sourcing_cost_usd=Decimal("0.00"),
                weighted_lateness_ticks=weighted_lateness_ticks,
                lateness_penalty_usd=lateness_penalty.quantize(Decimal("0.01")),
                bay_blocked_ticks=bay_blocked_ticks,
                bay_blocked_penalty_usd=bay_blocked_penalty,
                schedule_churn_score=churn_score,
                schedule_churn_penalty_usd=churn_penalty,
                churn_status=churn_status,
                net_objective_usd=solver_obj_usd,
                objective_completeness="FULL_OBJECTIVE" if len(unconfigured_terms) == 0 else "PARTIAL_CONFIGURED",
                configured_terms=configured_terms,
                unconfigured_terms=unconfigured_terms,
                ro_completion_statuses=ro_completion_statuses,
                uncompleted_ros_count=uncompleted_ros_count,
            )

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

            # Dual Independent Verification (Primary Task E)
            oracle = SweepLineOracle(snapshot)
            verification_result = oracle.verify_plan(candidate_plan)

            supp_oracle = SupplementalAuditOracle(snapshot, ev)
            supp_result = supp_oracle.audit_plan(candidate_plan, planned_movements=planned_movements)

            has_assignments = len(assignments) > 0
            has_incomplete = any((t.status.value if hasattr(t.status, "value") else str(t.status)) != "COMPLETED" for t in snapshot.tasks)

            is_verified = verification_result.is_valid and (has_assignments or not has_incomplete)
            is_fully_certified = is_verified and supp_result.is_valid
            is_actionable = has_assignments and is_fully_certified and (len(supp_result.coverage_gaps) == 0) and getattr(supp_result, "is_actionable", True)

            # Optimality gap
            gap = 0.0
            if solver_status == SolverStatus.FEASIBLE and abs(solver_obj_cents) > 1e-6:
                gap = abs(best_bound_cents - solver_obj_cents) / abs(solver_obj_cents)

            if is_fully_certified:
                return ScheduleResult(
                    plan_id=plan_id,
                    rooftop_id=snapshot.rooftop.rooftop_id,
                    snapshot_hash=snapshot.snapshot_hash or "",
                    solver_tier=SchedulerTier.T2_CPSAT,
                    solver_status=solver_status,
                    runtime_ms=round(solve_elapsed_ms, 3),
                    objective_value_usd=solver_obj_usd,
                    best_bound_usd=best_bound_usd,
                    optimality_gap=round(gap, 4),
                    plan=candidate_plan,
                    planned_movements=planned_movements,
                    metrics=metrics,
                    unscheduled_tasks=unscheduled_reasons,
                    verification_result=verification_result,
                    is_verified=True,
                    supplemental_audit_result=supp_result.model_dump(),
                    is_fully_certified=True,
                    is_actionable=is_actionable,
                    evidence_coverage_gaps=supp_result.coverage_gaps,
                    ro_completion_statuses=ro_completion_statuses,
                )
            else:
                # T2 candidate failed dual verification! Discard and fall back to T1
                t1_fallback_res = self.t1_fallback.schedule(
                    snapshot,
                    plan_id=f"{plan_id}-T1-FALLBACK",
                    evidence=ev,
                    blocked_bay_intervals=blocked_intervals,
                )
                t1_fallback_res.degradation_reason = (
                    f"T2 CP-SAT candidate failed L4 verification (L4 valid={is_verified}, Supp valid={supp_result.is_valid}); "
                    f"reverted to T1 constructive schedule."
                )
                return t1_fallback_res

        # If solver returned INFEASIBLE or UNKNOWN, fall back to T1
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
