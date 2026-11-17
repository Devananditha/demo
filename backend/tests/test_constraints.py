"""Unit Tests for Shared Constraint Library C1–C7."""

from decimal import Decimal
import pytest

from app.constraints.rules import (
    ViolationCode,
    check_c1_bay_compatibility,
    check_c1_technician_skill,
    check_c2_part_ready,
    check_c3_precedence,
    check_c5_vehicle_movement,
    check_c6_technician_break,
    check_c6_technician_shift,
    check_c7_customer_authorization,
    check_c7_freight_threshold,
    check_c7_snapshot_concurrency,
    check_intervals_overlap,
)


class TestC1EligibilityGate:
    def test_technician_skill_match_success(self):
        ok, code, msg = check_c1_technician_skill(["EV", "DIAGNOSTIC", "MECHANICAL"], "EV")
        assert ok is True
        assert code is None

    def test_technician_skill_mismatch_rejected(self):
        ok, code, msg = check_c1_technician_skill(["MAINTENANCE", "FLUIDS"], "EV")
        assert ok is False
        assert code == ViolationCode.C1_SKILL_INELIGIBLE
        assert "lacks required skill" in msg

    def test_technician_empty_skills_fails_closed(self):
        ok, code, msg = check_c1_technician_skill([], "BRAKES")
        assert ok is False
        assert code == ViolationCode.C1_SKILL_INELIGIBLE

    def test_bay_compatibility_success(self):
        ok, code, msg = check_c1_bay_compatibility(
            bay_type="HEAVY_DIAGNOSTIC_LIFT",
            required_bay_type="HEAVY_DIAGNOSTIC_LIFT",
            is_operational=True,
            lifting_capacity_lbs=12000,
            vehicle_weight_lbs=5000,
        )
        assert ok is True
        assert code is None

    def test_bay_type_mismatch_rejected(self):
        ok, code, msg = check_c1_bay_compatibility(
            bay_type="STANDARD_2POST",
            required_bay_type="HEAVY_DIAGNOSTIC_LIFT",
        )
        assert ok is False
        assert code == ViolationCode.C1_BAY_TYPE_INELIGIBLE

    def test_bay_inoperative_rejected(self):
        ok, code, msg = check_c1_bay_compatibility(
            bay_type="STANDARD_2POST",
            required_bay_type="STANDARD_2POST",
            is_operational=False,
        )
        assert ok is False
        assert code == ViolationCode.C1_BAY_INOPERATIVE

    def test_bay_lifting_capacity_exceeded_rejected(self):
        ok, code, msg = check_c1_bay_compatibility(
            bay_type="STANDARD_2POST",
            required_bay_type="STANDARD_2POST",
            lifting_capacity_lbs=8000,
            vehicle_weight_lbs=9500,
        )
        assert ok is False
        assert code == ViolationCode.C1_BAY_CAPACITY_EXCEEDED


class TestC2PartReadiness:
    def test_task_start_after_usable_ready_success(self):
        ok, code, msg = check_c2_part_ready(task_start_tick=165, usable_ready_tick=165)
        assert ok is True
        assert code is None

        ok2, _, _ = check_c2_part_ready(task_start_tick=170, usable_ready_tick=165)
        assert ok2 is True

    def test_task_start_before_usable_ready_rejected(self):
        ok, code, msg = check_c2_part_ready(task_start_tick=160, usable_ready_tick=165)
        assert ok is False
        assert code == ViolationCode.C2_PART_NOT_READY
        assert "before part is usable-ready" in msg

    def test_unconfirmed_usable_tick_rejected(self):
        ok, code, msg = check_c2_part_ready(task_start_tick=100, usable_ready_tick=None)
        assert ok is False
        assert code == ViolationCode.C2_PART_NOT_READY


class TestC3PrecedenceDAG:
    def test_successor_after_predecessor_success(self):
        ok, code, msg = check_c3_precedence(predecessor_end_tick=108, successor_start_tick=108)
        assert ok is True
        assert code is None

    def test_successor_before_predecessor_rejected(self):
        ok, code, msg = check_c3_precedence(predecessor_end_tick=108, successor_start_tick=100)
        assert ok is False
        assert code == ViolationCode.C3_PRECEDENCE_VIOLATION


class TestC4IntervalOverlap:
    def test_overlapping_intervals_detected(self):
        assert check_intervals_overlap(96, 114, 108, 126) is True

    def test_contiguous_intervals_do_not_overlap(self):
        assert check_intervals_overlap(96, 108, 108, 126) is False

    def test_disjoint_intervals_do_not_overlap(self):
        assert check_intervals_overlap(96, 108, 120, 132) is False


class TestC5VehiclePhysicalMovement:
    def test_immobilized_vehicle_same_bay_success(self):
        ok, code, msg = check_c5_vehicle_movement("IMMOBILIZED_ON_LIFT", "BAY-01", "BAY-01")
        assert ok is True
        assert code is None

    def test_immobilized_vehicle_relocation_rejected(self):
        ok, code, msg = check_c5_vehicle_movement("IMMOBILIZED_ON_LIFT", "BAY-01", "BAY-02")
        assert ok is False
        assert code == ViolationCode.C5_ILLEGAL_VEHICLE_MOVE

    def test_rollable_vehicle_relocation_success(self):
        ok, code, msg = check_c5_vehicle_movement("ROLLABLE", "BAY-01", "BAY-02")
        assert ok is True

    def test_unknown_state_vehicle_relocation_rejected(self):
        ok, code, msg = check_c5_vehicle_movement("UNKNOWN", "BAY-01", "BAY-02")
        assert ok is False
        assert code == ViolationCode.C5_UNKNOWN_STATE_MOVE


class TestC6TechnicianShiftsAndBreaks:
    def test_task_within_shift_success(self):
        ok, code, msg = check_c6_technician_shift(
            task_start_tick=96,
            task_end_tick=114,
            shift_start_tick=96,
            shift_end_tick=204,
        )
        assert ok is True

    def test_task_before_shift_start_rejected(self):
        ok, code, msg = check_c6_technician_shift(
            task_start_tick=90,
            task_end_tick=114,
            shift_start_tick=96,
            shift_end_tick=204,
        )
        assert ok is False
        assert code == ViolationCode.C6_OUTSIDE_SHIFT

    def test_task_after_shift_end_rejected_without_overtime(self):
        ok, code, msg = check_c6_technician_shift(
            task_start_tick=192,
            task_end_tick=216,
            shift_start_tick=96,
            shift_end_tick=204,
            allow_overtime=False,
        )
        assert ok is False
        assert code == ViolationCode.C6_OUTSIDE_SHIFT

    def test_task_after_shift_end_allowed_with_emergency_overtime(self):
        ok, code, msg = check_c6_technician_shift(
            task_start_tick=192,
            task_end_tick=216,
            shift_start_tick=96,
            shift_end_tick=204,
            allow_overtime=True,
            overtime_cutoff_tick=228,
        )
        assert ok is True

    def test_meal_break_overlap_rejected(self):
        ok, code, msg = check_c6_technician_break(
            task_start_tick=140,
            task_end_tick=150,
            lunch_start_tick=144,
            lunch_duration_ticks=12,
        )
        assert ok is False
        assert code == ViolationCode.C6_BREAK_WINDOW_BREACH

    def test_pre_lunch_and_post_lunch_tasks_success(self):
        # Pre-lunch finishes exactly at 144
        ok1, _, _ = check_c6_technician_break(120, 144, 144, 12)
        assert ok1 is True
        # Post-lunch starts exactly at 156 (144 + 12)
        ok2, _, _ = check_c6_technician_break(156, 180, 144, 12)
        assert ok2 is True


class TestC7AuthorityApprovalsAndOCC:
    def test_customer_authorization(self):
        ok, _, _ = check_c7_customer_authorization(True)
        assert ok is True

        unauth, code, _ = check_c7_customer_authorization(False)
        assert unauth is False
        assert code == ViolationCode.C7_UNAUTHORIZED_REPAIR

    def test_freight_threshold(self):
        # $37 below $50 threshold -> OK without manager approval
        ok, _, _ = check_c7_freight_threshold(Decimal("37.00"), Decimal("50.00"), False)
        assert ok is True

        # $75 above $50 threshold -> Rejected without manager approval
        rej, code, _ = check_c7_freight_threshold(Decimal("75.00"), Decimal("50.00"), False)
        assert rej is False
        assert code == ViolationCode.C7_FREIGHT_LIMIT_EXCEEDED

        # $75 above $50 threshold -> OK with manager approval
        appr, _, _ = check_c7_freight_threshold(Decimal("75.00"), Decimal("50.00"), True)
        assert appr is True

    def test_snapshot_concurrency_revalidation(self):
        hash_val = "ff91917b566997906e220f9cb04e9353b5bff9ab1dadddf1e2fc3ab772351ffb"
        ok, _, _ = check_c7_snapshot_concurrency(hash_val, hash_val)
        assert ok is True

        stale, code, _ = check_c7_snapshot_concurrency(hash_val, "0000000000000000000000000000000000000000000000000000000000000000")
        assert stale is False
        assert code == ViolationCode.C7_STALE_SNAPSHOT_HASH
