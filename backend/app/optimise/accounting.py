"""Shared Canonical Objective Accounting for ServiceYield AI.

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 3: Optimise)
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/14_FINANCIAL_MODEL_AND_ASSUMPTIONS.md

Unified Formulation:
    Z = Gross Labor Contribution
      - Customer Lateness Penalty
      - Sourcing / Expedited Freight Cost
      - Bay Blocked Idle Penalty
      - Schedule Churn Penalty
"""

from decimal import Decimal
from typing import Optional


def compute_net_economic_objective(
    gross_contribution_usd: Decimal,
    lateness_penalty_usd: Decimal,
    sourcing_cost_usd: Decimal = Decimal("0.00"),
    bay_blocked_penalty_usd: Decimal = Decimal("0.00"),
    schedule_churn_penalty_usd: Decimal = Decimal("0.00"),
    bay_blocked_cost_usd: Optional[Decimal] = None,
    churn_cost_usd: Optional[Decimal] = None,
) -> Decimal:
    """Computes total net economic yield Z in USD with exact decimal precision.
    
    Guarantees that reporting, heuristic evaluation, Decision Replay, and benchmark metrics
    use the exact same economic terms and sign conventions as the CP-SAT integer program.
    """
    gross = gross_contribution_usd or Decimal("0.00")
    lateness = lateness_penalty_usd or Decimal("0.00")
    sourcing = sourcing_cost_usd or Decimal("0.00")
    blocked = bay_blocked_cost_usd if bay_blocked_cost_usd is not None else (bay_blocked_penalty_usd or Decimal("0.00"))
    churn = churn_cost_usd if churn_cost_usd is not None else (schedule_churn_penalty_usd or Decimal("0.00"))

    net = gross - lateness - sourcing - blocked - churn
    return net.quantize(Decimal("0.01"))
