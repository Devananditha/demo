"""Bay-Hour Shadow Price nu_b(t) Discrete Re-Solve Calculation Engine.

Authoritative Reference:
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.3)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md (A3: $120/hr sold labor, nu = $2.00/min = $120/hr)
- docs/18_PHASED_IMPLEMENTATION_ROADMAP.md (Task 1.4)

Mathematical Formulation:
In discrete mathematical programming (OR-Tools CP-SAT integer programming),
true continuous dual variables do not exist directly. Therefore, nu_b(t)
is computed via a discrete re-solve difference procedure:

    nu_b(t) = (Z*(C) - Z*(C \\ {(b, t)})) / Delta_t

Where:
- Z*(C) is the baseline optimal net objective value with bay b available.
- Z*(C \\ {(b, t)}) is the perturbed optimal net objective value with bay b blocked during [t1, t2).
- Delta_t is the evaluation duration in decimal hours (Delta_ticks / 12).
- Canonical storage unit: USD per bay-hour (e.g. $120.00/hour).
- Internal solver unit: USD per bay-tick (nu_hour / 12 = $10.00/tick).
- Exactness certification:
  - status = EXACT (is_exact = True) if and only if BOTH paired solves are genuine T2 CP-SAT solves,
    both prove mathematical OPTIMAL, both pass L4 sweep-line verification, and Delta Z >= 0.
  - status = APPROXIMATE (is_exact = False) if either solve stopped at FEASIBLE.
  - status = UNAVAILABLE (is_exact = False) if either solve returned INFEASIBLE/UNKNOWN or Delta Z < 0.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from app.optimise.config import OptimiseConfig
from app.optimise.cpsat_solver import CPSATScheduler
from app.optimise.evidence import WorkshopEvidenceBundle
from app.optimise.models import (
    BayHourPriceSurface,
    BayHourShadowPrice,
    ScheduleResult,
    SchedulerTier,
    ShadowPriceStatus,
    SolverStatus,
)
from app.schemas.domain import DealershipSnapshotSchema


class BayHourShadowPriceCalculator:
    """Discrete difference re-solve engine for bay capacity valuation."""

    def __init__(
        self,
        config: Optional[OptimiseConfig] = None,
        solver: Optional[CPSATScheduler] = None,
    ):
        self.config = config or OptimiseConfig()
        self.solver = solver or CPSATScheduler(self.config)

    def calculate_shadow_price(
        self,
        snapshot: DealershipSnapshotSchema,
        bay_id: str,
        start_tick: int,
        end_tick: int,
        baseline_result: Optional[ScheduleResult] = None,
        evidence: Optional[WorkshopEvidenceBundle] = None,
    ) -> BayHourShadowPrice:
        """Computes the marginal economic value nu_b(t) of bay b during [start_tick, end_tick).

        Args:
            snapshot: Canonical validated dealership snapshot state.
            bay_id: Identifier of bay to evaluate.
            start_tick: Start of evaluation window (0 <= start_tick < end_tick <= 288).
            end_tick: End of evaluation window.
            baseline_result: Optional precomputed unperturbed baseline result.
            evidence: Explicit operational evidence bundle.

        Returns:
            BayHourShadowPrice with canonical USD/bay-hour valuation and exactness certification.
        """
        # 1. Validation
        if not (0 <= start_tick < end_tick <= self.config.horizon_ticks):
            raise ValueError(
                f"Invalid evaluation interval [{start_tick}, {end_tick}). "
                f"Must satisfy 0 <= start < end <= {self.config.horizon_ticks}."
            )

        bay_lookup = {b.bay_id: b for b in snapshot.bays}
        if bay_id not in bay_lookup:
            raise ValueError(f"Bay '{bay_id}' does not exist in snapshot bays.")

        ev = evidence or WorkshopEvidenceBundle(current_tick=snapshot.rooftop.operating_day_start_tick)
        delta_ticks = end_tick - start_tick
        duration_hours = (Decimal(str(delta_ticks)) / Decimal("12")).quantize(Decimal("0.0001"))

        # 2. Baseline Solve Z*(C)
        use_cached_baseline = False
        if baseline_result is not None:
            # Baseline must match snapshot hash, be a verified T2 CP-SAT solve, and be OPTIMAL
            if (
                baseline_result.snapshot_hash == (snapshot.snapshot_hash or "")
                and baseline_result.solver_tier == SchedulerTier.T2_CPSAT
                and baseline_result.is_verified is True
                and baseline_result.solver_status == SolverStatus.OPTIMAL
            ):
                use_cached_baseline = True
                base_res = baseline_result

        if not use_cached_baseline:
            base_res = self.solver.schedule(
                snapshot,
                plan_id=f"PLAN-SHADOW-BASE-{snapshot.rooftop.rooftop_id}",
                evidence=ev,
            )

        # 3. Perturbed Solve Z*(C \ {(b, [start, end))})
        pert_plan_id = f"PLAN-SHADOW-PERT-{bay_id}-{start_tick}-{end_tick}"
        pert_res = self.solver.schedule(
            snapshot,
            plan_id=pert_plan_id,
            evidence=ev,
            blocked_bay_intervals=[(bay_id, start_tick, end_tick)],
        )

        # 4. Status and Exactness Evaluation
        base_status = base_res.solver_status
        pert_status = pert_res.solver_status
        base_tier = base_res.solver_tier
        pert_tier = pert_res.solver_tier

        base_obj = base_res.objective_value_usd if base_res.objective_value_usd is not None else Decimal("0.00")
        pert_obj = pert_res.objective_value_usd if pert_res.objective_value_usd is not None else Decimal("0.00")
        signed_delta = base_obj - pert_obj

        # Strict exactness: genuine T2, both OPTIMAL, both verified, non-negative difference
        if signed_delta < Decimal("-0.01"):
            # Significant negative difference implies solver non-monotonicity or inconsistency
            is_exact = False
            status = ShadowPriceStatus.UNAVAILABLE
            delta_obj = Decimal("0.00")
            nu_hour = Decimal("0.00")
            nu_tick = Decimal("0.0000")
            reason = (
                f"Shadow price unavailable due to solver inconsistency: "
                f"restricting capacity increased objective by ${abs(signed_delta)}."
            )
        elif (
            base_status == SolverStatus.OPTIMAL
            and pert_status == SolverStatus.OPTIMAL
            and base_tier == SchedulerTier.T2_CPSAT
            and pert_tier == SchedulerTier.T2_CPSAT
            and base_res.is_verified
            and pert_res.is_verified
        ):
            is_exact = True
            status = ShadowPriceStatus.EXACT
            delta_obj = max(Decimal("0.00"), signed_delta).quantize(Decimal("0.01"))
            nu_hour = (delta_obj / duration_hours).quantize(Decimal("0.01"))
            nu_tick = (nu_hour / Decimal("12")).quantize(Decimal("0.0001"))
            if delta_obj == Decimal("0.00"):
                reason = (
                    f"Bay {bay_id} is non-binding during [{start_tick}, {end_tick}): "
                    f"workshop possesses surplus bay capacity; loss incurs $0.00 yield impact."
                )
            else:
                reason = (
                    f"Bay {bay_id} is a binding bottleneck during [{start_tick}, {end_tick}): "
                    f"capacity restriction reduces net yield by ${delta_obj} "
                    f"(${nu_hour}/bay-hour)."
                )
        elif (
            base_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
            and pert_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
            and base_res.is_verified
            and pert_res.is_verified
        ):
            is_exact = False
            status = ShadowPriceStatus.APPROXIMATE
            delta_obj = max(Decimal("0.00"), signed_delta).quantize(Decimal("0.01"))
            nu_hour = (delta_obj / duration_hours).quantize(Decimal("0.01"))
            nu_tick = (nu_hour / Decimal("12")).quantize(Decimal("0.0001"))
            reason = (
                f"Shadow price approximate: solver returned FEASIBLE (baseline={base_status.value}, "
                f"perturbed={pert_status.value}, baseline_tier={base_tier.value}, perturbed_tier={pert_tier.value})."
            )
        else:
            is_exact = False
            status = ShadowPriceStatus.UNAVAILABLE
            delta_obj = Decimal("0.00")
            nu_hour = Decimal("0.00")
            nu_tick = Decimal("0.0000")
            reason = (
                f"Shadow price unavailable: solver returned non-feasible or unverified status "
                f"(baseline={base_status.value}, perturbed={pert_status.value})."
            )

        return BayHourShadowPrice(
            rooftop_id=snapshot.rooftop.rooftop_id,
            bay_id=bay_id,
            interval_start_tick=start_tick,
            interval_end_tick=end_tick,
            duration_hours=duration_hours,
            shadow_price_usd_per_hour=nu_hour,
            shadow_price_usd_per_tick=nu_tick,
            baseline_objective_usd=base_obj,
            perturbed_objective_usd=pert_obj,
            delta_objective_usd=delta_obj,
            signed_delta_objective_usd=signed_delta,
            is_exact=is_exact,
            status=status,
            baseline_status=base_status,
            perturbed_status=pert_status,
            objective_coverage="PARTIAL_CONFIGURED",
            reason=reason,
            computed_at=datetime.now(timezone.utc),
        )

    def compute_price_surface(
        self,
        snapshot: DealershipSnapshotSchema,
        bay_ids: Optional[List[str]] = None,
        interval_ticks: int = 12,
        stride_ticks: int = 3,
        horizon_start_tick: Optional[int] = None,
        horizon_end_tick: Optional[int] = None,
        evidence: Optional[WorkshopEvidenceBundle] = None,
    ) -> BayHourPriceSurface:
        """Computes a discrete shadow price surface across operational bays and operating intervals.

        Args:
            snapshot: Canonical validated dealership snapshot.
            bay_ids: Optional subset of bays to evaluate (defaults to all operational bays).
            interval_ticks: Length of each evaluation window in ticks (default 12 ticks = 1 hour).
            stride_ticks: Step size between window starts in ticks (default 3 ticks = 15 minutes).
            horizon_start_tick: Earliest tick to evaluate (defaults to snapshot operating_day_start_tick).
            horizon_end_tick: Latest tick to evaluate (defaults to snapshot operating_day_end_tick).
            evidence: Explicit operational evidence bundle.

        Returns:
            BayHourPriceSurface containing mapped discrete valuation points.
        """
        ev = evidence or WorkshopEvidenceBundle(current_tick=snapshot.rooftop.operating_day_start_tick)

        if bay_ids is None:
            target_bays = [b.bay_id for b in snapshot.bays if b.is_operational]
        else:
            target_bays = [b_id for b_id in bay_ids if any(b.bay_id == b_id and b.is_operational for b in snapshot.bays)]

        start_bound = horizon_start_tick if horizon_start_tick is not None else snapshot.rooftop.operating_day_start_tick
        end_bound = horizon_end_tick if horizon_end_tick is not None else snapshot.rooftop.operating_day_end_tick

        baseline_res = self.solver.schedule(
            snapshot,
            plan_id=f"PLAN-SURFACE-BASE-{snapshot.rooftop.rooftop_id}",
            evidence=ev,
        )

        points: List[BayHourShadowPrice] = []
        for bay_id in target_bays:
            curr_start = start_bound
            while curr_start + interval_ticks <= end_bound:
                curr_end = curr_start + interval_ticks
                point = self.calculate_shadow_price(
                    snapshot=snapshot,
                    bay_id=bay_id,
                    start_tick=curr_start,
                    end_tick=curr_end,
                    baseline_result=baseline_res,
                    evidence=ev,
                )
                points.append(point)
                curr_start += stride_ticks

        return BayHourPriceSurface(
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            points=points,
            stride_ticks=stride_ticks,
            computed_at=datetime.now(timezone.utc),
        )
