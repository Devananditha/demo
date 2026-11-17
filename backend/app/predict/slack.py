"""Operational Slack Analyzer for ServiceYield AI.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 2.3: Layer 1 Deterministic Baseline)
- Technical Report Section 6.1 (Module 1: Predict)

Formulations:
  Slack = Latest Feasible Start (LFS) - Usable-Ready Time
  LFS = Promise Tick - Critical Path Remaining Duration Ticks

Thresholds:
  Slack < 0 minutes: BLOCKED (deadline breach physically inevitable without intervention)
  Slack < 30 minutes (6 ticks): AT_RISK (jeopardized by operational variation)
  P(delay) > tau_raise (0.25): AT_RISK
"""

from typing import Dict, List, Optional, Sequence, Set
from app.predict.models import OperationalSlack, QuantileInterval
from app.schemas.domain import RepairOrderSchema, TaskSchema


SLACK_BLOCKED_THRESHOLD_TICKS: int = 0  # < 0 min
SLACK_AT_RISK_THRESHOLD_TICKS: int = 6  # 30 min = 6 ticks (6 * 5 = 30m)
TAU_RAISE: float = 0.25                 # Default probability threshold to raise AT_RISK
TAU_CLEAR: float = 0.15                 # Threshold to clear AT_RISK to prevent flapping


class SlackAnalyzer:
    """Computes critical path remaining durations, latest feasible starts, and operational slacks."""

    @staticmethod
    def calculate_remaining_duration_ticks(tasks: Sequence[TaskSchema]) -> int:
        """Calculates total remaining labor duration ticks across incomplete tasks.
        
        Considers tasks with status PENDING, IN_PROGRESS, or STALLED.
        """
        incomplete_tasks = [
            t for t in tasks
            if (t.status.value if hasattr(t.status, "value") else str(t.status)) in {"PENDING", "IN_PROGRESS", "STALLED"}
        ]
        if not incomplete_tasks:
            return 0

        # Build task duration map and predecessor graph
        durations: Dict[str, int] = {t.task_id: t.estimated_duration_ticks for t in incomplete_tasks}
        predecessors: Dict[str, List[str]] = {t.task_id: t.predecessor_task_ids for t in incomplete_tasks}

        # Dynamic programming for longest path (critical path) in DAG
        memo: Dict[str, int] = {}

        def get_path_duration(task_id: str, visited: Set[str]) -> int:
            if task_id in memo:
                return memo[task_id]
            if task_id in visited:
                # Cycle guard fallback
                return durations.get(task_id, 0)

            visited.add(task_id)
            preds = predecessors.get(task_id, [])
            incomplete_preds = [p for p in preds if p in durations]

            if not incomplete_preds:
                path_len = durations.get(task_id, 0)
            else:
                path_len = durations.get(task_id, 0) + max(
                    get_path_duration(p, visited.copy()) for p in incomplete_preds
                )

            memo[task_id] = path_len
            return path_len

        # Critical path is the max path ending at any sink task in the incomplete set
        critical_path_ticks = max((get_path_duration(t_id, set()) for t_id in durations), default=0)
        return critical_path_ticks

    @classmethod
    def calculate_latest_feasible_start(
        cls,
        repair_order: RepairOrderSchema,
        tasks: Sequence[TaskSchema],
    ) -> int:
        """Calculates the latest feasible start tick before customer promise is breached.
        
        LFS = promise_tick - remaining_duration_ticks
        """
        ro_tasks = [t for t in tasks if t.ro_id == repair_order.ro_id]
        remaining_duration = cls.calculate_remaining_duration_ticks(ro_tasks)
        lfs = repair_order.promise_tick - remaining_duration
        return max(0, lfs)

    @staticmethod
    def compute_slack(
        latest_feasible_start_tick: int,
        usable_ready_tick: Optional[int],
        quantiles: Optional[QuantileInterval] = None,
    ) -> OperationalSlack:
        """Computes deterministic operational slack in both ticks and minutes."""
        if usable_ready_tick is None:
            return OperationalSlack(
                latest_feasible_start_tick=latest_feasible_start_tick,
                usable_ready_tick=None,
                slack_ticks=None,
                slack_minutes=None,
            )

        slack_ticks = latest_feasible_start_tick - usable_ready_tick
        slack_minutes = slack_ticks * 5

        slack_p10 = None
        slack_p50 = None
        slack_p90 = None

        if quantiles:
            # Conservative P10 slack corresponds to high P90 arrival tick
            slack_p10 = latest_feasible_start_tick - quantiles.p90
            slack_p50 = latest_feasible_start_tick - quantiles.p50
            slack_p90 = latest_feasible_start_tick - quantiles.p10

        return OperationalSlack(
            latest_feasible_start_tick=latest_feasible_start_tick,
            usable_ready_tick=usable_ready_tick,
            slack_ticks=slack_ticks,
            slack_minutes=slack_minutes,
            slack_p10_ticks=slack_p10,
            slack_p50_ticks=slack_p50,
            slack_p90_ticks=slack_p90,
        )
