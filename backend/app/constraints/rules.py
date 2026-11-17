"""ServiceYield AI Canonical Shared Constraint Definitions (C1–C7).

Authoritative Reference:
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- Technical Report Sections 5.2, 5.4, 14.2
- Product Blueprint Section 6

This module provides the pure-Python, zero-solver constraint evaluation library.
Predict, Optimise, Recover, and the L4 Independent Verifier all import and evaluate
these exact hard constraint semantics.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


class ViolationCode(str, Enum):
    """Canonical error and violation codes emitted when hard constraints are breached."""
    # C1 — Eligibility Gate
    C1_SKILL_INELIGIBLE = "C1_SKILL_INELIGIBLE"
    C1_BAY_TYPE_INELIGIBLE = "C1_BAY_TYPE_INELIGIBLE"
    C1_BAY_CAPACITY_EXCEEDED = "C1_BAY_CAPACITY_EXCEEDED"
    C1_BAY_INOPERATIVE = "C1_BAY_INOPERATIVE"

    # C2 — Part Timing
    C2_PART_NOT_READY = "C2_PART_NOT_READY"

    # C3 — Precedence DAG
    C3_PRECEDENCE_VIOLATION = "C3_PRECEDENCE_VIOLATION"

    # C4 — Resource Exclusivity
    C4_BAY_DOUBLE_BOOKED = "C4_BAY_DOUBLE_BOOKED"
    C4_TECH_DOUBLE_BOOKED = "C4_TECH_DOUBLE_BOOKED"

    # C5 — Vehicle Physical State & Movement
    C5_ILLEGAL_VEHICLE_MOVE = "C5_ILLEGAL_VEHICLE_MOVE"
    C5_UNKNOWN_STATE_MOVE = "C5_UNKNOWN_STATE_MOVE"

    # C6 — Technician Shifts & Breaks
    C6_OUTSIDE_SHIFT = "C6_OUTSIDE_SHIFT"
    C6_BREAK_WINDOW_BREACH = "C6_BREAK_WINDOW_BREACH"

    # C7 — Authority & Approvals
    C7_UNAUTHORIZED_REPAIR = "C7_UNAUTHORIZED_REPAIR"
    C7_FREIGHT_LIMIT_EXCEEDED = "C7_FREIGHT_LIMIT_EXCEEDED"
    C7_STALE_SNAPSHOT_HASH = "C7_STALE_SNAPSHOT_HASH"


@dataclass(frozen=True)
class ConstraintViolation:
    """Detailed record of a constraint violation caught during schedule verification."""
    code: ViolationCode
    constraint: str  # "C1", "C2", ..., "C7"
    message: str
    entity_id: Optional[str] = None
    tick: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "constraint": self.constraint,
            "message": self.message,
            "entity_id": self.entity_id,
            "tick": self.tick,
            "context": self.context,
        }


# ============================================================================
# C1: ELIGIBILITY GATE (Skills, Bays, Capacities)
# ============================================================================

def check_c1_technician_skill(
    technician_skills: Sequence[str],
    required_skill: str,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C1: Checks if technician holds the certified skill required for an operation.
    
    Fails closed: if skills are missing or empty, evaluates to False.
    """
    if not technician_skills:
        return False, ViolationCode.C1_SKILL_INELIGIBLE, "Technician has no certified skills registered."
    
    if required_skill not in technician_skills:
        return (
            False,
            ViolationCode.C1_SKILL_INELIGIBLE,
            f"Technician lacks required skill '{required_skill}'. Possesses: {list(technician_skills)}.",
        )
    return True, None, "Skill match verified."


def check_c1_bay_compatibility(
    bay_type: str,
    required_bay_type: str,
    is_operational: bool = True,
    lifting_capacity_lbs: int = 10000,
    vehicle_weight_lbs: int = 4000,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C1: Checks if service bay is operational, matches required type, and supports vehicle weight."""
    if not is_operational:
        return False, ViolationCode.C1_BAY_INOPERATIVE, "Bay is marked non-operational."

    if bay_type != required_bay_type:
        return (
            False,
            ViolationCode.C1_BAY_TYPE_INELIGIBLE,
            f"Bay type '{bay_type}' does not match required '{required_bay_type}'.",
        )

    if vehicle_weight_lbs > lifting_capacity_lbs:
        return (
            False,
            ViolationCode.C1_BAY_CAPACITY_EXCEEDED,
            f"Vehicle weight ({vehicle_weight_lbs} lbs) exceeds bay lifting capacity ({lifting_capacity_lbs} lbs).",
        )

    return True, None, "Bay compatibility verified."


# ============================================================================
# C2: PART RELEASE & USABLE-READY TIMING
# ============================================================================

def check_c2_part_ready(
    task_start_tick: int,
    usable_ready_tick: Optional[int],
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C2: Checks that task execution does not start before required parts are usable-ready."""
    if usable_ready_tick is None:
        return (
            False,
            ViolationCode.C2_PART_NOT_READY,
            "Required part has no confirmed usable_ready_tick (unfulfilled or unquoted).",
        )
    if task_start_tick < usable_ready_tick:
        return (
            False,
            ViolationCode.C2_PART_NOT_READY,
            f"Task scheduled to start at tick {task_start_tick} before part is usable-ready at tick {usable_ready_tick}.",
        )
    return True, None, "Part usable readiness verified."


# ============================================================================
# C3: OPERATION PRECEDENCE (Task DAG)
# ============================================================================

def check_c3_precedence(
    predecessor_end_tick: int,
    successor_start_tick: int,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C3: Checks that a successor task begins only after its predecessor completes."""
    if successor_start_tick < predecessor_end_tick:
        return (
            False,
            ViolationCode.C3_PRECEDENCE_VIOLATION,
            f"Successor starts at tick {successor_start_tick} before predecessor finishes at tick {predecessor_end_tick}.",
        )
    return True, None, "Precedence order verified."


# ============================================================================
# C4: RESOURCE EXCLUSIVITY & TIME OVERLAPS
# ============================================================================

def check_intervals_overlap(
    start1: int,
    end1: int,
    start2: int,
    end2: int,
) -> bool:
    """Checks whether half-open discrete intervals [start1, end1) and [start2, end2) overlap.
    
    Adjoining intervals [0, 10) and [10, 20) do NOT overlap.
    """
    return max(start1, start2) < min(end1, end2)


# C4 overlap alias for standardized naming
check_c4_overlap = check_intervals_overlap


# ============================================================================
# C5: VEHICLE PHYSICAL STATE & MOVEMENT
# ============================================================================

def check_c5_vehicle_movement(
    physical_state: str,
    currently_assigned_bay_id: Optional[str],
    target_bay_id: str,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C5: Validates vehicle movement rules against its physical condition.
    
    If vehicle is IMMOBILIZED_ON_LIFT:
      Cannot be relocated to another bay or returned to holding while immobilized.
    If vehicle is UNKNOWN:
      Prohibits automated vehicle movements.
    """
    if physical_state == "IMMOBILIZED_ON_LIFT":
        if currently_assigned_bay_id and target_bay_id != currently_assigned_bay_id:
            return (
                False,
                ViolationCode.C5_ILLEGAL_VEHICLE_MOVE,
                f"Vehicle is IMMOBILIZED_ON_LIFT in bay '{currently_assigned_bay_id}' and cannot be moved to bay '{target_bay_id}'.",
            )
    elif physical_state == "UNKNOWN":
        if currently_assigned_bay_id != target_bay_id:
            return (
                False,
                ViolationCode.C5_UNKNOWN_STATE_MOVE,
                "Vehicle physical state is UNKNOWN. Automated vehicle movement is prohibited.",
            )
    return True, None, "Vehicle movement legality verified."


# ============================================================================
# C6: TECHNICIAN SHIFTS & MANDATORY BREAKS
# ============================================================================

def check_c6_technician_shift(
    task_start_tick: int,
    task_end_tick: int,
    shift_start_tick: int,
    shift_end_tick: int,
    allow_overtime: bool = False,
    overtime_cutoff_tick: Optional[int] = None,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C6: Checks that task execution falls strictly within the technician's working hours."""
    if task_start_tick < shift_start_tick:
        return (
            False,
            ViolationCode.C6_OUTSIDE_SHIFT,
            f"Task starts at tick {task_start_tick} before technician shift start {shift_start_tick}.",
        )
    
    max_allowed_end = overtime_cutoff_tick if (allow_overtime and overtime_cutoff_tick) else shift_end_tick
    if task_end_tick > max_allowed_end:
        return (
            False,
            ViolationCode.C6_OUTSIDE_SHIFT,
            f"Task finishes at tick {task_end_tick} past allowed working boundary {max_allowed_end} (shift end {shift_end_tick}).",
        )
    return True, None, "Shift boundary verified."


def check_c6_technician_break(
    task_start_tick: int,
    task_end_tick: int,
    lunch_start_tick: int,
    lunch_duration_ticks: int = 12,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C6: Checks that task does not overlap the technician's mandatory meal break window."""
    lunch_end_tick = lunch_start_tick + lunch_duration_ticks
    if check_intervals_overlap(task_start_tick, task_end_tick, lunch_start_tick, lunch_end_tick):
        return (
            False,
            ViolationCode.C6_BREAK_WINDOW_BREACH,
            f"Task [{task_start_tick}, {task_end_tick}) overlaps technician mandatory meal break [{lunch_start_tick}, {lunch_end_tick}).",
        )
    return True, None, "Technician meal break non-overlap verified."


# ============================================================================
# C7: AUTHORITY, APPROVALS & OCC CONCURRENCY
# ============================================================================

def check_c7_customer_authorization(
    is_authorized: bool,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C7: Checks that customer has authorized the repair operation."""
    if not is_authorized:
        return (
            False,
            ViolationCode.C7_UNAUTHORIZED_REPAIR,
            "Customer estimate authorization has not been granted for this repair.",
        )
    return True, None, "Customer repair authorization verified."


def check_c7_freight_threshold(
    freight_surcharge_usd: Decimal,
    threshold_usd: Decimal = Decimal("50.00"),
    is_manager_approved: bool = False,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C7: Checks if expedited freight surcharge exceeds threshold without approval."""
    if freight_surcharge_usd > threshold_usd and not is_manager_approved:
        return (
            False,
            ViolationCode.C7_FREIGHT_LIMIT_EXCEEDED,
            f"Expedited freight surcharge (${freight_surcharge_usd:.2f}) exceeds policy threshold (${threshold_usd:.2f}) without manager sign-off.",
        )
    return True, None, "Freight policy authorization verified."


def check_c7_snapshot_concurrency(
    plan_snapshot_hash: str,
    current_state_hash: str,
) -> Tuple[bool, Optional[ViolationCode], str]:
    """C7: Optimistic Concurrency Control (OCC) revalidation against state mutations."""
    if plan_snapshot_hash != current_state_hash:
        return (
            False,
            ViolationCode.C7_STALE_SNAPSHOT_HASH,
            f"OCC concurrency failure: Plan snapshot hash ({plan_snapshot_hash[:8]}...) does not match fresh state hash ({current_state_hash[:8]}...).",
        )
    return True, None, "State snapshot concurrency verified."
