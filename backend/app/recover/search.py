"""Admissible Two-Layer Branch-and-Bound Sourcing Search Engine.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md (Section 2.3)
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
"""

import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from app.optimise.config import OptimiseConfig
from app.optimise.evidence import WorkshopEvidenceBundle
from app.recover.models import SourcingCandidate, SourcingSearchResult
from app.schemas.domain import (
    DealershipSnapshotSchema,
    PartRequirementSchema,
    QuoteStatus,
    RepairOrderSchema,
    SupplierOfferSchema,
    TaskSchema,
    VehiclePhysicalState,
)


class SourcingSearchEngine:
    """Two-layer admissible branch-and-bound search for supplier sourcing alternatives.
    
    Implements:
    - Layer 1: Infinite-Capacity Critical-Path Lower Bound (LB_CP)
    - Layer 2: Parallel-Bay Preemptive Scheduling Lower Bound (LB_Preempt)
    """

    def __init__(self, config: Optional[OptimiseConfig] = None):
        self.config = config or OptimiseConfig()
        # Financial coefficients:
        # A3: $120.00 / hour = $10.00 / tick
        self.labor_rate_tick_usd = (self.config.labor_contribution_per_hour_usd / Decimal("12")).quantize(Decimal("0.01"))
        # S-MATH-01: $0.50 / minute = $2.50 / tick
        self.lateness_penalty_tick_usd = (self.config.lateness_penalty_per_minute_usd * Decimal("5.00")).quantize(Decimal("0.01"))

    def search_sourcing_alternatives(
        self,
        snapshot: DealershipSnapshotSchema,
        disrupted_ro_id: str,
        disrupted_part_req_id: Optional[str] = None,
        current_tick: Optional[int] = None,
        evidence: Optional[WorkshopEvidenceBundle] = None,
        best_known_loss_bound: Optional[Decimal] = None,
        evaluation_time_utc: Optional[datetime] = None,
    ) -> SourcingSearchResult:
        """Executes admissible two-layer branch-and-bound search across supplier offers."""
        start_time = time.perf_counter()
        curr_tick = current_tick if current_tick is not None else (
            evidence.current_tick if evidence else snapshot.rooftop.operating_day_start_tick
        )
        # 1. Identify Target Part Requirement
        target_part = self._resolve_target_part(snapshot, disrupted_ro_id, disrupted_part_req_id)
        if not target_part:
            return SourcingSearchResult(
                disrupted_part_req_id=disrupted_part_req_id or "UNKNOWN",
                evaluated_offers_count=0,
                feasible_candidates=[],
                pruned_candidates=[],
                rejected_candidates=[],
                search_duration_ms=0.0,
            )

        # 2. Extract Repair Order, Task DAG & Workload Metrics
        ro = next((r for r in snapshot.repair_orders if r.ro_id == disrupted_ro_id), None)
        if not ro:
            raise ValueError(f"Repair order '{disrupted_ro_id}' not found in snapshot.")

        if evaluation_time_utc is not None:
            eval_time = evaluation_time_utc
        elif evidence and getattr(evidence, "evaluation_timestamp_utc", None):
            eval_time = evidence.evaluation_timestamp_utc
        elif ro and ro.updated_at:
            eval_time = ro.updated_at
        else:
            eval_time = datetime.now(timezone.utc)

        remaining_duration_ticks = self._compute_remaining_dag_duration(snapshot, ro.ro_id, target_part.task_id)
        competing_ro, competing_duration, competing_is_holding = self._find_competing_bay_workload(snapshot, ro)

        # 3. Evaluate Available Supplier Offers
        offers = [o for o in snapshot.supplier_offers if o.part_req_id == target_part.part_req_id]
        feasible: List[SourcingCandidate] = []
        pruned: List[SourcingCandidate] = []
        rejected: List[SourcingCandidate] = []

        for offer in offers:
            # Check hard eligibility constraints
            is_valid, reject_reason = self._validate_offer_eligibility(offer, target_part, eval_time)
            if not is_valid:
                rejected.append(
                    SourcingCandidate(
                        option_id=offer.offer_id,
                        offer_id=offer.offer_id,
                        part_req_id=offer.part_req_id,
                        supplier_id=offer.supplier_id,
                        supplier_name=offer.supplier_name,
                        unit_cost_usd=offer.unit_cost_usd,
                        freight_surcharge_usd=offer.freight_surcharge_usd,
                        total_sourcing_cost_usd=offer.unit_cost_usd + offer.freight_surcharge_usd,
                        quoted_eta_tick=offer.quoted_eta_tick,
                        receiving_inspection_minutes=offer.receiving_inspection_minutes,
                        usable_ready_tick=offer.usable_ready_tick or offer.quoted_eta_tick,
                        is_feasible=False,
                        rejection_reason=reject_reason,
                    )
                )
                continue

            usable_tick = offer.usable_ready_tick or offer.quoted_eta_tick
            effective_start = max(curr_tick, usable_tick)
            freight = offer.freight_surcharge_usd

            # -------------------------------------------------------------
            # Layer 1: Infinite-Capacity Critical-Path Bound (LB_CP)
            # -------------------------------------------------------------
            ro_earliest_finish = effective_start + remaining_duration_ticks
            ro_lateness_ticks = max(0, ro_earliest_finish - ro.promise_tick)
            ro_lateness_penalty_usd = (
                Decimal(str(ro.priority_weight)) * Decimal(str(ro_lateness_ticks)) * self.lateness_penalty_tick_usd
            )
            lb_cp = (ro_lateness_penalty_usd + freight).quantize(Decimal("0.01"))

            # -------------------------------------------------------------
            # Layer 2: Parallel-Bay Preemptive Scheduling Lower Bound (LB_Preempt)
            # -------------------------------------------------------------
            competing_penalty_usd = Decimal("0.00")
            if competing_ro and ro.assigned_bay_id:
                # Competing vehicle cannot access the bay until disrupted RO vacates
                move_delay = 2 if competing_is_holding else 0
                comp_earliest_start = ro_earliest_finish + move_delay
                comp_earliest_finish = comp_earliest_start + competing_duration
                
                # Check horizon boundary (emergency overtime cutoff)
                horizon_cutoff = self.config.overtime_cutoff_tick if self.config.allow_emergency_overtime else self.config.horizon_end_tick
                if comp_earliest_finish > horizon_cutoff:
                    # Vehicle cannot be completed in horizon -> full lost gross contribution!
                    comp_gross = (
                        Decimal(str(competing_duration)) * self.labor_rate_tick_usd
                    ).quantize(Decimal("0.01"))
                    competing_penalty_usd = comp_gross
                else:
                    comp_lateness_ticks = max(0, comp_earliest_finish - competing_ro.promise_tick)
                    competing_penalty_usd = (
                        Decimal(str(competing_ro.priority_weight))
                        * Decimal(str(comp_lateness_ticks))
                        * self.lateness_penalty_tick_usd
                    ).quantize(Decimal("0.01"))

            lb_preempt = (ro_lateness_penalty_usd + competing_penalty_usd + freight).quantize(Decimal("0.01"))
            lb_combined = max(lb_cp, lb_preempt)

            candidate = SourcingCandidate(
                option_id=offer.offer_id,
                offer_id=offer.offer_id,
                part_req_id=offer.part_req_id,
                supplier_id=offer.supplier_id,
                supplier_name=offer.supplier_name,
                unit_cost_usd=offer.unit_cost_usd,
                freight_surcharge_usd=freight,
                total_sourcing_cost_usd=offer.unit_cost_usd + freight,
                quoted_eta_tick=offer.quoted_eta_tick,
                receiving_inspection_minutes=offer.receiving_inspection_minutes,
                usable_ready_tick=usable_tick,
                is_feasible=True,
                critical_path_lower_bound_usd=lb_cp,
                parallel_bay_lower_bound_usd=lb_preempt,
                combined_lower_bound_usd=lb_combined,
            )

            # -------------------------------------------------------------
            # Branch-and-Bound Pruning Gate
            # -------------------------------------------------------------
            if best_known_loss_bound is not None and lb_combined > best_known_loss_bound:
                candidate.is_pruned = True
                candidate.pruning_reason = (
                    f"Combined lower bound ${lb_combined} exceeds incumbent loss bound ${best_known_loss_bound}."
                )
                pruned.append(candidate)
            else:
                feasible.append(candidate)

        # 4. Deterministic Priority Ranking (Lowest lower-bound penalty/loss first)
        feasible.sort(key=lambda c: (c.combined_lower_bound_usd, c.usable_ready_tick, c.freight_surcharge_usd, c.offer_id))

        best_id = feasible[0].option_id if feasible else None
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SourcingSearchResult(
            disrupted_part_req_id=target_part.part_req_id,
            evaluated_offers_count=len(offers),
            feasible_candidates=feasible,
            pruned_candidates=pruned,
            rejected_candidates=rejected,
            best_candidate_id=best_id,
            search_duration_ms=round(elapsed_ms, 3),
        )

    def _resolve_target_part(
        self,
        snapshot: DealershipSnapshotSchema,
        ro_id: str,
        part_req_id: Optional[str] = None,
    ) -> Optional[PartRequirementSchema]:
        """Resolves the disrupted part requirement entity from the snapshot."""
        if part_req_id:
            for p in snapshot.part_requirements:
                if p.part_req_id == part_req_id:
                    return p
            return None
        
        # If part_req_id not explicitly given, find parts assigned to this RO
        ro_parts = [p for p in snapshot.part_requirements if p.ro_id == ro_id]
        if ro_parts:
            # Prefer parts linked to stalled/in-progress tasks or with latest arrival
            return ro_parts[0]
        return None

    def _validate_offer_eligibility(
        self,
        offer: SupplierOfferSchema,
        target_part: PartRequirementSchema,
        eval_time: datetime,
    ) -> Tuple[bool, Optional[str]]:
        """Strictly validates offer eligibility under C1 and C7 hard gates."""
        if offer.part_req_id != target_part.part_req_id:
            return False, f"Part requirement mismatch: expected {target_part.part_req_id}, got {offer.part_req_id}"

        status_val = offer.quote_status.value if hasattr(offer.quote_status, "value") else str(offer.quote_status)
        if status_val != QuoteStatus.ACTIVE.value:
            return False, f"Supplier quote status is not ACTIVE (status={status_val})"

        if offer.quote_valid_until:
            valid_until = offer.quote_valid_until if offer.quote_valid_until.tzinfo else offer.quote_valid_until.replace(tzinfo=timezone.utc)
            if valid_until < eval_time:
                return False, f"Supplier quote expired at {valid_until.isoformat()}"

        if offer.usable_ready_tick is not None and offer.usable_ready_tick > self.config.horizon_ticks:
            return False, f"Usable ready tick {offer.usable_ready_tick} exceeds horizon bounds ({self.config.horizon_ticks})"

        return True, None

    def _compute_remaining_dag_duration(
        self,
        snapshot: DealershipSnapshotSchema,
        ro_id: str,
        target_task_id: str,
    ) -> int:
        """Computes the topological longest path duration in the RO task DAG starting from target task."""
        ro_tasks = {t.task_id: t for t in snapshot.tasks if t.ro_id == ro_id}
        if target_task_id not in ro_tasks:
            return 0

        # Successor adjacency
        successors: Dict[str, List[str]] = {t_id: [] for t_id in ro_tasks}
        for t_id, task in ro_tasks.items():
            for p_id in task.predecessor_task_ids:
                if p_id in successors:
                    successors[p_id].append(t_id)

        # Memoized longest path
        memo: Dict[str, int] = {}

        def get_longest_path(curr_id: str) -> int:
            if curr_id in memo:
                return memo[curr_id]
            dur = ro_tasks[curr_id].estimated_duration_ticks
            child_max = 0
            for succ_id in successors.get(curr_id, []):
                child_max = max(child_max, get_longest_path(succ_id))
            memo[curr_id] = dur + child_max
            return memo[curr_id]

        return get_longest_path(target_task_id)

    def _find_competing_bay_workload(
        self,
        snapshot: DealershipSnapshotSchema,
        ro: RepairOrderSchema,
    ) -> Tuple[Optional[RepairOrderSchema], int, bool]:
        """Identifies competing repair orders blocked by the disrupted RO's bay occupancy."""
        state_val = ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state)
        if state_val != VehiclePhysicalState.IMMOBILIZED_ON_LIFT.value or not ro.assigned_bay_id:
            return None, 0, False

        assigned_bay = next((b for b in snapshot.bays if b.bay_id == ro.assigned_bay_id), None)
        if not assigned_bay:
            return None, 0, False

        # Find competing ROs requiring the exact same bay or bay type
        competing: List[Tuple[RepairOrderSchema, int, bool]] = []
        for other_ro in snapshot.repair_orders:
            if other_ro.ro_id == ro.ro_id:
                continue
            other_tasks = [t for t in snapshot.tasks if t.ro_id == other_ro.ro_id and t.status.value != "COMPLETED"]
            if any(t.required_bay_type == assigned_bay.bay_type for t in other_tasks):
                total_dur = sum(t.estimated_duration_ticks for t in other_tasks)
                other_state = other_ro.physical_state.value if hasattr(other_ro.physical_state, "value") else str(other_ro.physical_state)
                is_holding = other_state == VehiclePhysicalState.IN_HOLDING.value
                competing.append((other_ro, total_dur, is_holding))

        if not competing:
            return None, 0, False

        # Return highest priority competing RO
        competing.sort(key=lambda x: (-x[0].priority_weight, x[0].promise_tick))
        return competing[0]
