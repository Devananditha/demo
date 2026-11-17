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

    def test_precedence_cycle_raises_value_error(self, base_ro):
        """Finding 6: Precedence cycles in task DAG must raise a clear ValueError."""
        tasks = [
            TaskSchema(
                task_id="T1",
                ro_id="RO-TEST-01",
                sequence_order=1,
                operation_code="OP-1",
                description="Task 1",
                required_skill="BRAKES",
                required_bay_type="STANDARD_2POST",
                flat_rate_minutes=60,
                estimated_duration_ticks=12,
                status=TaskStatus.PENDING,
                predecessor_task_ids=["T2"],  # T1 depends on T2
                version=1,
            ),
            TaskSchema(
                task_id="T2",
                ro_id="RO-TEST-01",
                sequence_order=2,
                operation_code="OP-2",
                description="Task 2",
                required_skill="BRAKES",
                required_bay_type="STANDARD_2POST",
                flat_rate_minutes=60,
                estimated_duration_ticks=12,
                status=TaskStatus.PENDING,
                predecessor_task_ids=["T1"],  # T2 depends on T1 -> CYCLE!
                version=1,
            ),
        ]
        with pytest.raises(ValueError, match="Precedence cycle detected"):
            SlackAnalyzer.calculate_latest_feasible_start(base_ro, tasks)

    def test_negative_lfs_when_overdue(self, base_ro):
        """Finding 6: When promise tick < remaining duration, LFS is negative (not clamped to 0)."""
        tasks = [
            TaskSchema(
                task_id="T1",
                ro_id="RO-TEST-01",
                sequence_order=1,
                operation_code="OP-1",
                description="Task 1",
                required_skill="BRAKES",
                required_bay_type="STANDARD_2POST",
                flat_rate_minutes=120,
                estimated_duration_ticks=50,
                status=TaskStatus.PENDING,
                version=1,
            ),
        ]
        # base_ro promise_tick = 30, remaining duration = 50 -> LFS = 30 - 50 = -20
        overdue_ro = base_ro.model_copy(deep=True)
        overdue_ro.promise_tick = 30
        lfs = SlackAnalyzer.calculate_latest_feasible_start(overdue_ro, tasks)
        assert lfs == -20

    def test_evaluation_slack_with_current_tick(self):
        """Finding 6: Evaluation slack computes LFS - current_tick."""
        slack = SlackAnalyzer.compute_slack(
            latest_feasible_start_tick=174,
            usable_ready_tick=159,
            current_tick=159,
        )
        assert slack.slack_ticks == 15
        assert slack.slack_minutes == 75
        assert slack.evaluation_slack_ticks == 15
        assert slack.evaluation_slack_minutes == 75

        # If current_tick is past LFS:
        late_slack = SlackAnalyzer.compute_slack(
            latest_feasible_start_tick=150,
            usable_ready_tick=140,
            current_tick=160,
        )
        assert late_slack.slack_ticks == 10  # 150 - 140 = 10 buffer ticks
        assert late_slack.evaluation_slack_ticks == -10  # 150 - 160 = -10 (overdue to start)
        assert late_slack.evaluation_slack_minutes == -50
