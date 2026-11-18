"""ServiceYield AI — Optimise Engine (Phase 1, Task 1.4).

Hierarchy:
- T1 Deterministic Earliest-Fit Bitset Scheduler (true integer bitset masks, < 2ms)
- T2 Discrete OR-Tools CP-SAT Optimizer (2.5s budget, warm-started with T1, dual verified)
- Bay-Hour Shadow Price nu_b(t) Discrete Difference Re-Solve Engine
- Independent Supplemental Audit Oracle and Explicit Workshop Evidence Contracts
"""

from app.optimise.config import OptimiseConfig
from app.optimise.cpsat_solver import CPSATScheduler
from app.optimise.evidence import (
    CustomerAuthorizationEvidence,
    ManagerFreightApprovalEvidence,
    TaskExecutionProgressEvidence,
    TechnicianFairnessEvidence,
    VehicleMovementEvidence,
    VehiclePhysicalEvidence,
    WorkshopEvidenceBundle,
)
from app.optimise.heuristics import BitsetOccupancyGrid, T1BitsetScheduler
from app.optimise.models import (
    BayHourPriceSurface,
    BayHourShadowPrice,
    ObjectiveMetrics,
    PlannedVehicleMovement,
    RepairOrderCompletionStatus,
    ScheduleResult,
    SchedulerTier,
    ShadowPriceStatus,
    SolverStatus,
)
from app.optimise.shadow_price import BayHourShadowPriceCalculator
from app.optimise.supplemental_audit import (
    CertificationStatus,
    SupplementalAuditOracle,
    SupplementalAuditResult,
)

__all__ = [
    "OptimiseConfig",
    "T1BitsetScheduler",
    "BitsetOccupancyGrid",
    "CPSATScheduler",
    "BayHourShadowPriceCalculator",
    "SupplementalAuditOracle",
    "SupplementalAuditResult",
    "CertificationStatus",
    "WorkshopEvidenceBundle",
    "CustomerAuthorizationEvidence",
    "ManagerFreightApprovalEvidence",
    "TaskExecutionProgressEvidence",
    "VehiclePhysicalEvidence",
    "VehicleMovementEvidence",
    "TechnicianFairnessEvidence",
    "ScheduleResult",
    "PlannedVehicleMovement",
    "ObjectiveMetrics",
    "SchedulerTier",
    "SolverStatus",
    "ShadowPriceStatus",
    "RepairOrderCompletionStatus",
    "BayHourShadowPrice",
    "BayHourPriceSurface",
]
