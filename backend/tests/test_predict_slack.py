"""Unit Tests for Slack Analyzer."""

from datetime import datetime, timezone
import pytest

from app.predict.models import QuantileInterval
from app.predict.slack import (
    SLACK_AT_RISK_THRESHOLD_TICKS,
    SLACK_BLOCKED_THRESHOLD_TICKS,
    SlackAnalyzer,
)
from app.schemas.domain import RepairOrderSchema, ROStatus, TaskSchema, TaskStatus, VehiclePhysicalState


@pytest.fixture
def base_ro():
    return RepairOrderSchema(
        ro_id="RO-TEST-01",
        rooftop_id="ROOF-01",
        vehicle_id="VEH-01",
        customer_id="CUST-01",
        complaint="Transmission diagnosis",
        promised_at=datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc),
        promise_tick=192,
        priority_weight=1,
        status=ROStatus.OPEN,
        physical_state=VehiclePhysicalState.ROLLABLE,
        assigned_bay_id=None,
        version=1,
        updated_at=datetime(2026, 11, 18, 8, 0, tzinfo=timezone.utc),
    )


class TestSlackAnalyzer:
    def test_single_task_latest_feasible_start(self, base_ro):
        tasks = [
            TaskSchema(
                task_id="T1",
                ro_id="RO-TEST-01",
                sequence_order=1,
                operation_code="OP-1",
                description="Desc",
                required_skill="BRAKES",
                required_bay_type="STANDARD_2POST",
                flat_rate_minutes=60,
                estimated_duration_ticks=12,
                status=TaskStatus.PENDING,
                version=1,
            )
        ]
        # LFS = promise_tick (192) - 12 = 180
        lfs = SlackAnalyzer.calculate_latest_feasible_start(base_ro, tasks)
        assert lfs == 180

    def test_multi_task_precedence_dag_lfs(self, base_ro):
        # Two sequential tasks: T1 (12 ticks, COMPLETED) -> T2 (24 ticks, STALLED)
        tasks = [
            TaskSchema(
                task_id="T1",
                ro_id="RO-TEST-01",
                sequence_order=1,
                operation_code="OP-1",
                description="Teardown",
                required_skill="TRANSMISSION",
                required_bay_type="HEAVY_DIAGNOSTIC_LIFT",
                flat_rate_minutes=60,
                estimated_duration_ticks=12,
                status=TaskStatus.COMPLETED,
                predecessor_task_ids=[],
                version=1,
            ),
            TaskSchema(
                task_id="T2",
                ro_id="RO-TEST-01",
                sequence_order=2,
                operation_code="OP-2",
                description="Reassembly",
                required_skill="TRANSMISSION",
                required_bay_type="HEAVY_DIAGNOSTIC_LIFT",
                flat_rate_minutes=120,
                estimated_duration_ticks=24,
                status=TaskStatus.STALLED,
                predecessor_task_ids=["T1"],
                version=1,
            ),
        ]
        # T1 is COMPLETED, so remaining duration is only T2 (24 ticks)
        # LFS = 192 - 24 = 168 (exactly the S-MATH-01 RO-104 LFS!)
        lfs = SlackAnalyzer.calculate_latest_feasible_start(base_ro, tasks)
        assert lfs == 168

    def test_compute_slack_positive(self):
        # LFS = 180, Usable Ready = 160 -> Slack = +20 ticks = +100 min
        slack = SlackAnalyzer.compute_slack(latest_feasible_start_tick=180, usable_ready_tick=160)
        assert slack.slack_ticks == 20
        assert slack.slack_minutes == 100

    def test_compute_slack_negative_blocked(self):
        # LFS = 168, Usable Ready = 198 -> Slack = -30 ticks = -150 min
        slack = SlackAnalyzer.compute_slack(latest_feasible_start_tick=168, usable_ready_tick=198)
        assert slack.slack_ticks == -30
        assert slack.slack_minutes == -150
        assert slack.slack_ticks < SLACK_BLOCKED_THRESHOLD_TICKS

    def test_compute_slack_at_risk_boundary_30_minutes(self):
        # LFS = 170, Usable Ready = 165 -> Slack = +5 ticks = +25 min (< 30m -> AT_RISK)
        slack = SlackAnalyzer.compute_slack(latest_feasible_start_tick=170, usable_ready_tick=165)
        assert slack.slack_ticks == 5
        assert slack.slack_minutes == 25
        assert slack.slack_ticks < SLACK_AT_RISK_THRESHOLD_TICKS

        # LFS = 171, Usable Ready = 165 -> Slack = +6 ticks = +30 min (boundary)
        slack_bound = SlackAnalyzer.compute_slack(latest_feasible_start_tick=171, usable_ready_tick=165)
        assert slack_bound.slack_ticks == 6
        assert slack_bound.slack_minutes == 30
        assert slack_bound.slack_ticks >= SLACK_AT_RISK_THRESHOLD_TICKS

    def test_compute_slack_with_quantiles(self):
        q = QuantileInterval(p10=160, p50=165, p90=175)
        slack = SlackAnalyzer.compute_slack(latest_feasible_start_tick=180, usable_ready_tick=165, quantiles=q)
        # slack_p10 = 180 - 175 = 5 ticks
        # slack_p50 = 180 - 165 = 15 ticks
        # slack_p90 = 180 - 160 = 20 ticks
        assert slack.slack_p10_ticks == 5
        assert slack.slack_p50_ticks == 15
        assert slack.slack_p90_ticks == 20

    def test_missing_usable_ready_tick_handled_safely(self):
        slack = SlackAnalyzer.compute_slack(latest_feasible_start_tick=180, usable_ready_tick=None)
        assert slack.usable_ready_tick is None
        assert slack.slack_ticks is None
        assert slack.slack_minutes is None
