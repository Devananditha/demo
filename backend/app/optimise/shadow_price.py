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

Strict Exactness Certification:
A shadow price may be certified EXACT if and only if:
1. Baseline is T2 CP-SAT.
2. Perturbed solve is T2 CP-SAT.
3. Both solves prove mathematical OPTIMAL.
4. Both pass L4 Sweep-Line Oracle and Supplemental Audit Oracle.
5. Both use identical snapshot and evidence contracts.
If Delta Z < -0.01 USD (solver non-monotonicity), status must be UNAVAILABLE.
If either solve returned FEASIBLE, status must be APPROXIMATE.
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
        """Computes the marginal economic value nu_b(t) of bay b during [start_tick, end_tick)."""
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
            if (
                baseline_result.snapshot_hash == (snapshot.snapshot_hash or "")
                and baseline_result.solver_tier == SchedulerTier.T2_CPSAT
                and getattr(baseline_result, "is_verified", False) is True
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
            is_exact = False
            status = ShadowPriceStatus.UNAVAILABLE
            delta_obj = signed_delta
            nu_hour = (signed_delta / duration_hours).quantize(Decimal("0.01"))
            nu_tick = (nu_hour / Decimal("12")).quantize(Decimal("0.0001"))
            reason = (
                f"Shadow price unavailable due to solver inconsistency: "
                f"restricting capacity produced negative delta ${signed_delta}."
            )
        elif (
            base_status == SolverStatus.OPTIMAL
            and pert_status == SolverStatus.OPTIMAL
            and base_tier == SchedulerTier.T2_CPSAT
            and pert_tier == SchedulerTier.T2_CPSAT
            and getattr(base_res, "is_verified", False)
            and getattr(pert_res, "is_verified", False)
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
                    f"capacity restriction reduces net yield by ${delta_obj} (${nu_hour}/bay-hour)."
                )
        elif (
            base_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
            and pert_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
            and getattr(base_res, "is_verified", False)
            and getattr(pert_res, "is_verified", False)
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
            objective_coverage=getattr(base_res.metrics, "objective_completeness", "PARTIAL_CONFIGURED"),
            reason=reason,
            computed_at=datetime.now(timezone.utc),
        )

    def calculate_price_surface(
        self,
        snapshot: DealershipSnapshotSchema,
        bay_id: Optional[str] = None,
        bay_ids: Optional[List[str]] = None,
        interval_ticks: int = 12,
        stride_ticks: Optional[int] = None,
        horizon_start_tick: Optional[int] = None,
        horizon_end_tick: Optional[int] = None,
        evidence: Optional[WorkshopEvidenceBundle] = None,
    ) -> BayHourPriceSurface:
        """Evaluates shadow price across the operating day using configured stride intervals."""
        stride = stride_ticks or self.config.shadow_price_valuation_stride_ticks
        ev = evidence or WorkshopEvidenceBundle(current_tick=snapshot.rooftop.operating_day_start_tick)

        start_boundary = horizon_start_tick if horizon_start_tick is not None else snapshot.rooftop.operating_day_start_tick
        end_boundary = (
            horizon_end_tick
            if horizon_end_tick is not None
            else (
                snapshot.rooftop.overtime_cutoff_tick
                if self.config.allow_emergency_overtime
                else snapshot.rooftop.operating_day_end_tick
            )
        )

        target_bays: List[str] = []
        if bay_ids:
            target_bays = bay_ids
        elif bay_id:
            target_bays = [bay_id]
        else:
            target_bays = [b.bay_id for b in snapshot.bays if b.is_operational]

        base_res = self.solver.schedule(
            snapshot,
            plan_id=f"PLAN-SURFACE-BASE-{snapshot.rooftop.rooftop_id}",
            evidence=ev,
        )

        points: List[BayHourShadowPrice] = []
        max_start = end_boundary - interval_ticks
        for target_b in target_bays:
            for tick in range(start_boundary, max_start + 1, stride):
                t_end = tick + interval_ticks
                point = self.calculate_shadow_price(
                    snapshot=snapshot,
                    bay_id=target_b,
                    start_tick=tick,
                    end_tick=t_end,
                    baseline_result=base_res,
                    evidence=ev,
                )
                points.append(point)

        return BayHourPriceSurface(
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
            points=points,
            stride_ticks=stride,
            computed_at=datetime.now(timezone.utc),
        )

    # Public alias
    compute_price_surface = calculate_price_surface
