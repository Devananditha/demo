"""ServiceYield AI — Optimise Engine (Phase 1, Task 1.4).

Hierarchy:
- T1 Deterministic Earliest-Fit Bitset Scheduler (< 2ms)
- T2 Discrete OR-Tools CP-SAT Optimizer (2.5s budget, warm-started with T1, L4 verified)
- Bay-Hour Shadow Price nu_b(t) Discrete Difference Re-Solve Engine
"""

from app.optimise.config import OptimiseConfig
from app.optimise.cpsat_solver import CPSATScheduler
from app.optimise.heuristics import BitsetOccupancyGrid, T1BitsetScheduler
from app.optimise.models import (
    BayHourPriceSurface,
    BayHourShadowPrice,
    ObjectiveMetrics,
    ScheduleResult,
    SchedulerTier,
    ShadowPriceStatus,
    SolverStatus,
)
from app.optimise.shadow_price import BayHourShadowPriceCalculator

__all__ = [
    "OptimiseConfig",
    "T1BitsetScheduler",
    "BitsetOccupancyGrid",
    "CPSATScheduler",
    "BayHourShadowPriceCalculator",
    "ScheduleResult",
    "ObjectiveMetrics",
    "SchedulerTier",
    "SolverStatus",
    "ShadowPriceStatus",
    "BayHourShadowPrice",
    "BayHourPriceSurface",
]
