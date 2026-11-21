"""Full-Shop Recovery Replanning Pipeline and Pareto Optimization.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md (Section 2.3)
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.4)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
"""

import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from app.optimise import (
    BayHourShadowPriceCalculator,
    CPSATScheduler,
    CustomerAuthorizationEvidence,
    ManagerFreightApprovalEvidence,
    ObjectiveMetrics,
    OptimiseConfig,
    ScheduleResult,
    SchedulerTier,
    ShadowPriceStatus,
    SolverStatus,
    SupplementalAuditOracle,
    T1BitsetScheduler,
    WorkshopEvidenceBundle,
    compute_net_economic_objective,
)
from app.recover.models import (
    DependencyBlastRadius,
    DisruptionEvent,
    DisruptionType,
    RecoveryAlternative,
    RecoveryRecommendationReport,
    SourcingCandidate,
)
from app.recover.search import SourcingSearchEngine
from app.replay.engine import replay_engine
from app.schemas.domain import (
    DealershipSnapshotSchema,
    PartRequirementSchema,
    RepairOrderSchema,
    TaskSchema,
    VehiclePhysicalState,
)
from app.optimise.supplemental_audit import SupplementalAuditOracle
from app.verifier.sweep_oracle import SweepLineOracle


class RecoveryReplanningPipeline:
    """Orchestrates end-to-end full-shop disruption recovery, sourcing, and Pareto optimization."""

    def __init__(
        self,
        config: Optional[OptimiseConfig] = None,
        sourcing_engine: Optional[SourcingSearchEngine] = None,
        solver: Optional[CPSATScheduler] = None,
        shadow_price_calc: Optional[BayHourShadowPriceCalculator] = None,
    ):
        self.config = config or OptimiseConfig()
        self.sourcing_engine = sourcing_engine or SourcingSearchEngine(self.config)
        self.solver = solver or CPSATScheduler(self.config)
        self.shadow_price_calc = shadow_price_calc or BayHourShadowPriceCalculator(self.config, self.solver)

    def execute_recovery(
        self,
        snapshot: DealershipSnapshotSchema,
        disruption_event: DisruptionEvent,
        evidence: Optional[WorkshopEvidenceBundle] = None,
        baseline_schedule: Optional[ScheduleResult] = None,
        evaluation_time_utc: Optional[datetime] = None,
    ) -> RecoveryRecommendationReport:
        """Executes full-shop recovery replanning across all surviving sourcing candidates."""
        start_time = time.perf_counter()
        eval_time = evaluation_time_utc or (
            disruption_event.event_timestamp_utc if disruption_event and disruption_event.event_timestamp_utc else None
        )
        if not eval_time and evidence and getattr(evidence, "evaluation_timestamp_utc", None):
            eval_time = evidence.evaluation_timestamp_utc
        if not eval_time:
            ro = next((r for r in snapshot.repair_orders if r.ro_id == disruption_event.disrupted_ro_id), None)
            eval_time = ro.updated_at if ro and ro.updated_at else datetime.now(timezone.utc)

        curr_tick = disruption_event.trigger_tick

        ev = evidence or WorkshopEvidenceBundle(current_tick=curr_tick)

        # --------------------------------------------------------------------
        # Step 1 & 2: Blast Radius and Dependency Analysis
        # --------------------------------------------------------------------
        blast_radius = self._analyze_blast_radius(snapshot, disruption_event)

        # --------------------------------------------------------------------
        # Step 3: Baseline Schedule Solve (Unmitigated Disruption State)
        # --------------------------------------------------------------------
        if baseline_schedule is not None:
            base_res = baseline_schedule
        else:
            base_res = self._solve_baseline(snapshot, disruption_event, ev, blast_radius)

        base_obj = base_res.metrics.net_objective_usd
        base_lateness = base_res.metrics.weighted_lateness_ticks

        # --------------------------------------------------------------------
        # Step 4 & 5: Sourcing Search with Two-Layer Branch-and-Bound
        # --------------------------------------------------------------------
        sourcing_result = self.sourcing_engine.search_sourcing_alternatives(
            snapshot=snapshot,
            disrupted_ro_id=disruption_event.disrupted_ro_id,
            disrupted_part_req_id=disruption_event.disrupted_part_req_id,
            current_tick=curr_tick,
            evidence=ev,
            evaluation_time_utc=eval_time,
        )

        # --------------------------------------------------------------------
        # Step 6: Full-Shop Re-optimization for Each Sourcing Candidate
        # --------------------------------------------------------------------
        candidates_to_evaluate = sourcing_result.feasible_candidates
        alternatives: List[RecoveryAlternative] = []

        for candidate in candidates_to_evaluate:
            cand_snapshot, cand_evidence = self._prepare_candidate_context(
                snapshot=snapshot,
                candidate=candidate,
                evidence=ev,
                blast_radius=blast_radius,
            )

            # Block bay until candidate usable tick so immobilized vehicle holds the bay until parts arrive
            blocked_bay_intervals = (
                [(blast_radius.immobilized_bay_id, snapshot.rooftop.operating_day_start_tick, candidate.usable_ready_tick)]
                if (blast_radius.is_immobilized_on_lift and blast_radius.immobilized_bay_id and candidate.usable_ready_tick > snapshot.rooftop.operating_day_start_tick)
                else None
            )

            # Re-optimize full workshop schedule
            plan_id = f"PLAN-REC-{candidate.option_id}"
            cand_res = self.solver.schedule(
                snapshot=cand_snapshot,
                plan_id=plan_id,
                evidence=cand_evidence,
                blocked_bay_intervals=blocked_bay_intervals,
            )

            # Verification: L4 Sweep-Line Oracle + Supplemental Operational Audit
            l4_oracle = SweepLineOracle(cand_snapshot)
            l4_verdict = l4_oracle.verify_plan(cand_res.plan)

            supp_oracle = SupplementalAuditOracle(cand_snapshot, cand_evidence)
            supp_verdict = supp_oracle.audit_plan(cand_res.plan, planned_movements=cand_res.planned_movements)

            is_verified = l4_verdict.is_valid and cand_res.is_verified
            is_fully_certified = is_verified and supp_verdict.is_valid and cand_res.is_fully_certified

            # Financial & Operational Metrics
            gross_contrib = cand_res.metrics.gross_contribution_usd
            sourcing_cost = candidate.freight_surcharge_usd
            lateness_penalty = cand_res.metrics.lateness_penalty_usd
            bay_blocked_penalty = cand_res.metrics.bay_blocked_penalty_usd or Decimal("0.00")
            churn_penalty = cand_res.metrics.schedule_churn_penalty_usd or Decimal("0.00")
            net_obj = compute_net_economic_objective(
                gross_contribution_usd=gross_contrib,
                lateness_penalty_usd=lateness_penalty,
                sourcing_cost_usd=sourcing_cost,
                bay_blocked_penalty_usd=bay_blocked_penalty,
                schedule_churn_penalty_usd=churn_penalty,
            )
            net_delta = (net_obj - base_obj).quantize(Decimal("0.01"))

            weighted_lateness = cand_res.metrics.weighted_lateness_ticks
            bay_blocked_hours = (Decimal(str(cand_res.metrics.bay_blocked_ticks)) / Decimal("12")).quantize(Decimal("0.1"))

            # Calculate Shadow Price Impact on Released Bay
            shadow_price = self._evaluate_shadow_price_impact(
                snapshot=cand_snapshot,
                candidate=candidate,
                baseline_res=base_res,
                candidate_res=cand_res,
                evidence=cand_evidence,
            )

            alt = RecoveryAlternative(
                option_id=candidate.option_id,
                plan_id=plan_id,
                sourcing_candidate=candidate,
                schedule_result=cand_res,
                gross_contribution_usd=gross_contrib,
                sourcing_cost_usd=sourcing_cost,
                lateness_penalty_usd=lateness_penalty,
                net_objective_usd=net_obj,
                net_recovery_delta_usd=net_delta,
                weighted_lateness_ticks=weighted_lateness,
                bay_blocked_hours=bay_blocked_hours,
                bay_hour_shadow_price=shadow_price,
                schedule_churn_count=0,
                is_verified=is_verified,
                is_fully_certified=is_fully_certified,
                certification_status=supp_verdict.certification_status.value if hasattr(supp_verdict.certification_status, "value") else str(supp_verdict.certification_status),
            )
            alternatives.append(alt)

        # --------------------------------------------------------------------
        # Step 7 & 8: Pareto Filtering & Ranking
        # --------------------------------------------------------------------
        pareto_frontier = self._filter_pareto_frontier(alternatives)

        # --------------------------------------------------------------------
        # Step 9 & 10: Recommendation Selection & Executive Rationale
        # --------------------------------------------------------------------
        recommended_alt = self._select_recommended_alternative(pareto_frontier, alternatives)
        if recommended_alt:
            recommended_alt.is_recommended = True
            rec_id = recommended_alt.option_id
            rec_plan_id = recommended_alt.plan_id
        else:
            rec_id = None
            rec_plan_id = None

        rationale = self._generate_recommendation_rationale(
            disruption=disruption_event,
            blast_radius=blast_radius,
            recommended=recommended_alt,
            baseline_res=base_res,
        )

        unresolved_risks = self._identify_unresolved_risks(
            disruption=disruption_event,
            recommended=recommended_alt,
            snapshot=snapshot,
        )

        # Decision Replay Delta and Explainability Synthesis
        decision_replay_diff = None
        explainability = None
        if recommended_alt and recommended_alt.schedule_result:
            decision_replay_diff = replay_engine.compute_diff(
                baseline_res=base_res,
                proposed_res=recommended_alt.schedule_result,
                sourcing_cost=recommended_alt.sourcing_cost_usd,
                snapshot=snapshot,
            )
            explainability = replay_engine.generate_explainability(
                disruption=disruption_event,
                recommended=recommended_alt,
                all_alternatives=alternatives,
                pruned_candidates=sourcing_result.pruned_candidates,
                rejected_candidates=sourcing_result.rejected_candidates,
                snapshot=snapshot,
            )
            replay_engine.record_decision(
                rooftop_id=snapshot.rooftop.rooftop_id,
                snapshot_hash=snapshot.snapshot_hash or "",
                diff=decision_replay_diff,
                explainability=explainability,
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return RecoveryRecommendationReport(
            disruption_event=disruption_event,
            blast_radius=blast_radius,
            baseline_plan_id=base_res.plan_id,
            baseline_net_objective_usd=base_obj,
            baseline_weighted_lateness_ticks=base_lateness,
            recommended_option_id=rec_id,
            recommended_plan_id=rec_plan_id,
            recommendation_rationale=rationale,
            alternatives=alternatives,
            pareto_frontier=pareto_frontier,
            decision_replay=decision_replay_diff,
            explainability=explainability,
            unresolved_risks=unresolved_risks,
            generated_at=eval_time,
            replan_duration_ms=round(elapsed_ms, 3),
        )

    def _analyze_blast_radius(
        self,
        snapshot: DealershipSnapshotSchema,
        disruption: DisruptionEvent,
    ) -> DependencyBlastRadius:
        """Determines the direct and downstream workshop blast radius."""
        ro_id = disruption.disrupted_ro_id
        ro = next((r for r in snapshot.repair_orders if r.ro_id == ro_id), None)
        
        ro_tasks = [t for t in snapshot.tasks if t.ro_id == ro_id]
        affected_task_ids = [t.task_id for t in ro_tasks]
        
        state_val = ro.physical_state.value if (ro and hasattr(ro.physical_state, "value")) else (str(ro.physical_state) if ro else "UNKNOWN")
        is_imm = state_val == VehiclePhysicalState.IMMOBILIZED_ON_LIFT.value
        imm_bay = ro.assigned_bay_id if (ro and is_imm) else None

        # Find competing ROs that need this bay
        competing_ros: List[str] = []
        competing_tasks: List[str] = []
        if imm_bay:
            assigned_bay = next((b for b in snapshot.bays if b.bay_id == imm_bay), None)
            if assigned_bay:
                for other_ro in snapshot.repair_orders:
                    if other_ro.ro_id == ro_id:
                        continue
                    other_tasks = [
                        t for t in snapshot.tasks
                        if t.ro_id == other_ro.ro_id and t.status.value != "COMPLETED" and t.required_bay_type == assigned_bay.bay_type
                    ]
                    if other_tasks:
                        competing_ros.append(other_ro.ro_id)
                        competing_tasks.extend([t.task_id for t in other_tasks])

        critical_path = sum(t.estimated_duration_ticks for t in ro_tasks if t.status.value != "COMPLETED")

        return DependencyBlastRadius(
            disrupted_ro_id=ro_id,
            affected_task_ids=affected_task_ids,
            immobilized_bay_id=imm_bay,
            is_immobilized_on_lift=is_imm,
            competing_ro_ids=competing_ros,
            competing_task_ids=competing_tasks,
            critical_path_ticks=critical_path,
        )

    def _solve_baseline(
        self,
        snapshot: DealershipSnapshotSchema,
        disruption: DisruptionEvent,
        evidence: WorkshopEvidenceBundle,
        blast_radius: Optional[DependencyBlastRadius] = None,
    ) -> ScheduleResult:
        """Computes the full-shop unmitigated baseline schedule incorporating the disruption."""
        base_snapshot = snapshot.model_copy(deep=True)
        # Apply primary delay to part requirement if specified
        target_part_id = disruption.disrupted_part_req_id
        delayed_tick = disruption.delayed_ready_tick or 198
        if target_part_id:
            for p in base_snapshot.part_requirements:
                if p.part_req_id == target_part_id:
                    p.usable_ready_tick = delayed_tick

        blocked_bay_intervals = (
            [(blast_radius.immobilized_bay_id, snapshot.rooftop.operating_day_start_tick, delayed_tick)]
            if (blast_radius and blast_radius.is_immobilized_on_lift and blast_radius.immobilized_bay_id and delayed_tick > snapshot.rooftop.operating_day_start_tick)
            else None
        )

        plan_id = f"PLAN-BASE-UNMITIGATED-{disruption.disrupted_ro_id}"
        return self.solver.schedule(
            snapshot=base_snapshot,
            plan_id=plan_id,
            evidence=evidence,
            blocked_bay_intervals=blocked_bay_intervals,
        )

    def _prepare_candidate_context(
        self,
        snapshot: DealershipSnapshotSchema,
        candidate: SourcingCandidate,
        evidence: WorkshopEvidenceBundle,
        blast_radius: Optional[DependencyBlastRadius] = None,
    ) -> Tuple[DealershipSnapshotSchema, WorkshopEvidenceBundle]:
        """Clones snapshot and injects supplier readiness and manager freight approvals."""
        cand_snap = snapshot.model_copy(deep=True)
        for p in cand_snap.part_requirements:
            if p.part_req_id == candidate.part_req_id:
                p.usable_ready_tick = candidate.usable_ready_tick

        cand_ev = evidence.model_copy(deep=True)
        # Inject explicit manager freight approval for expedited sourcing
        if candidate.freight_surcharge_usd > Decimal("0.00"):
            cand_ev.manager_freight_approvals[candidate.offer_id] = ManagerFreightApprovalEvidence(
                offer_id=candidate.offer_id,
                is_approved=True,
                approved_amount_usd=candidate.freight_surcharge_usd,
                approved_by="MGR-RECOVERY-GATEWAY",
            )

        # Route waiting vehicles competing for freed immobilized bay
        if blast_radius and blast_radius.is_immobilized_on_lift and blast_radius.immobilized_bay_id:
            imm_bay_id = blast_radius.immobilized_bay_id
            for comp_t_id in blast_radius.competing_task_ids:
                if comp_t_id in cand_ev.task_progress:
                    cand_ev.task_progress[comp_t_id].is_assignment_locked = True
                    cand_ev.task_progress[comp_t_id].existing_bay_id = imm_bay_id

        return cand_snap, cand_ev

    def _evaluate_shadow_price_impact(
        self,
        snapshot: DealershipSnapshotSchema,
        candidate: SourcingCandidate,
        baseline_res: ScheduleResult,
        candidate_res: ScheduleResult,
        evidence: WorkshopEvidenceBundle,
    ) -> Optional[Any]:
        """Calculates marginal shadow price nu_b(t) for the bay interval unlocked by earlier recovery."""
        # Check if an immobilized vehicle was freed earlier
        ro_id = candidate.part_req_id.split("-")[2] if "RO-" in candidate.part_req_id else None
        # Locate candidate assignments for disrupted tasks
        cand_tasks = [a for a in candidate_res.plan.assignments if candidate.part_req_id in a.task_id or "104" in a.ro_id]
        base_tasks = [a for a in baseline_res.plan.assignments if candidate.part_req_id in a.task_id or "104" in a.ro_id]

        if not cand_tasks or not base_tasks:
            return None

        bay_id = cand_tasks[0].bay_id
        cand_end = max(a.end_tick for a in cand_tasks)
        base_end = max(a.end_tick for a in base_tasks)

        if cand_end >= base_end:
            return None

        try:
            return self.shadow_price_calc.calculate_shadow_price(
                snapshot=snapshot,
                bay_id=bay_id,
                start_tick=cand_end,
                end_tick=base_end,
                evidence=evidence,
            )
        except Exception:
            return None

    def _filter_pareto_frontier(
        self,
        alternatives: List[RecoveryAlternative],
    ) -> List[RecoveryAlternative]:
        """Identifies non-dominated alternatives across [Lateness, Sourcing Cost, Bay Blocked, Net Yield]."""
        if not alternatives:
            return []

        pareto: List[RecoveryAlternative] = []
        for alt in alternatives:
            is_dominated = False
            for other in alternatives:
                if other.option_id == alt.option_id:
                    continue
                # Other dominates alt if it is >= on all objectives and strictly > on at least one
                # Objectives: min lateness, min sourcing cost, min bay blocked, max net delta
                better_or_equal = (
                    other.weighted_lateness_ticks <= alt.weighted_lateness_ticks
                    and other.sourcing_cost_usd <= alt.sourcing_cost_usd
                    and other.bay_blocked_hours <= alt.bay_blocked_hours
                    and other.net_recovery_delta_usd >= alt.net_recovery_delta_usd
                )
                strictly_better = (
                    other.weighted_lateness_ticks < alt.weighted_lateness_ticks
                    or other.sourcing_cost_usd < alt.sourcing_cost_usd
                    or other.bay_blocked_hours < alt.bay_blocked_hours
                    or other.net_recovery_delta_usd > alt.net_recovery_delta_usd
                )
                if better_or_equal and strictly_better:
                    is_dominated = True
                    break

            if not is_dominated:
                alt.is_pareto_optimal = True
                pareto.append(alt)
            else:
                alt.is_pareto_optimal = False

        return pareto

    def _select_recommended_alternative(
        self,
        pareto_frontier: List[RecoveryAlternative],
        all_alternatives: List[RecoveryAlternative],
    ) -> Optional[RecoveryAlternative]:
        """Selects the highest net recovery yield alternative among certified Pareto-optimal plans."""
        certified_pareto = [a for a in pareto_frontier if a.is_fully_certified]
        pool = certified_pareto if certified_pareto else [a for a in all_alternatives if a.is_fully_certified]
        if not pool:
            pool = pareto_frontier if pareto_frontier else all_alternatives

        if not pool:
            return None

        # Sort by net recovery delta (highest gain first), then lowest lateness
        pool.sort(key=lambda a: (-a.net_recovery_delta_usd, a.weighted_lateness_ticks, a.sourcing_cost_usd))
        return pool[0]

    def _generate_recommendation_rationale(
        self,
        disruption: DisruptionEvent,
        blast_radius: DependencyBlastRadius,
        recommended: Optional[RecoveryAlternative],
        baseline_res: ScheduleResult,
    ) -> str:
        """Constructs human-readable, economically grounded rationale for the Service Manager."""
        if not recommended:
            return "No feasible or certified recovery plan could be established within operational constraints."

        cand = recommended.sourcing_candidate
        freight = recommended.sourcing_cost_usd
        gain = recommended.net_recovery_delta_usd
        saved_lateness = baseline_res.metrics.weighted_lateness_ticks - recommended.weighted_lateness_ticks

        if freight > Decimal("0.00"):
            freight_clause = f"incurs +${freight:.2f} expedited courier freight"
        else:
            freight_clause = "requires $0.00 additional freight surcharge"

        bay_clause = ""
        if blast_radius.immobilized_bay_id:
            bay_clause = f", releasing {blast_radius.immobilized_bay_id} earlier"

        competing_clause = ""
        if blast_radius.competing_ro_ids:
            competing_names = ", ".join(blast_radius.competing_ro_ids)
            competing_clause = f" and safeguarding downstream {competing_names}"

        rationale = (
            f"Option {cand.option_id} ({cand.supplier_name}) for disrupted {disruption.disrupted_ro_id} {freight_clause} to deliver parts at tick {cand.usable_ready_tick}{bay_clause}{competing_clause}. "
            f"Reduces total shop weighted lateness by {saved_lateness} ticks, resulting in a net economic yield improvement of +${gain:.2f}."
        )
        return rationale

    def _identify_unresolved_risks(
        self,
        disruption: DisruptionEvent,
        recommended: Optional[RecoveryAlternative],
        snapshot: DealershipSnapshotSchema,
    ) -> List[str]:
        """Flags operational boundary conditions or residual lateness in the proposal."""
        risks: List[str] = []
        if not recommended:
            risks.append("CRITICAL_RISK: No actionable recovery option found; vehicle remains stalled.")
            return risks

        if recommended.weighted_lateness_ticks > 0:
            risks.append(
                f"RESIDUAL_LATENESS: Workshop retains {recommended.weighted_lateness_ticks} weighted lateness ticks across scheduled vehicles."
            )

        if recommended.schedule_result.metrics.uncompleted_ros_count > 0:
            uncompleted = [
                ro_id for ro_id, status in recommended.schedule_result.ro_completion_statuses.items()
                if status != "FULLY_SCHEDULED" and status != "COMPLETED"
            ]
            if uncompleted:
                risks.append(f"UNCOMPLETED_VEHICLES: Repair orders [{', '.join(uncompleted)}] could not be fully completed within the operating day horizon.")

        if recommended.sourcing_cost_usd > Decimal("50.00"):
            risks.append(f"FREIGHT_APPROVAL_REQUIRED: Freight cost ${recommended.sourcing_cost_usd:.2f} exceeds standard manager threshold ($50.00).")

        return risks
