"""Unit and Property Tests for Sourcing Search Engine (Branch-and-Bound).

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 4)
- docs/10_S_MATH_01_GOLDEN_FIXTURE.md
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from app.data.loader import load_fixture_data
from app.optimise.config import OptimiseConfig
from app.recover.search import SourcingSearchEngine
from app.schemas.domain import DealershipSnapshotSchema, QuoteStatus, SupplierOfferSchema
from tests.optimise_test_utils import make_synthetic_evidence


class TestSourcingSearchEngine:
    """Verifies two-layer branch-and-bound lower bounding, filtering, and pruning."""

    def test_sourcing_search_returns_ranked_candidates(self, validated_snapshot: DealershipSnapshotSchema):
        engine = SourcingSearchEngine()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        res = engine.search_sourcing_alternatives(
            snapshot=validated_snapshot,
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            current_tick=159,
            evidence=ev,
        )

        assert res.evaluated_offers_count == 2
        assert len(res.feasible_candidates) == 2
        assert len(res.rejected_candidates) == 0

        # S1 Hotshot courier should be ranked first because its lower-bound loss is lower
        best = res.feasible_candidates[0]
        assert best.offer_id == "OFFER-104-S1"
        assert best.usable_ready_tick == 165
        assert best.freight_surcharge_usd == Decimal("37.00")

        second = res.feasible_candidates[1]
        assert second.offer_id == "OFFER-104-S2"
        assert second.usable_ready_tick == 198
        assert second.freight_surcharge_usd == Decimal("0.00")

    def test_two_layer_lower_bounds_admissible(self, validated_snapshot: DealershipSnapshotSchema):
        engine = SourcingSearchEngine()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        res = engine.search_sourcing_alternatives(
            snapshot=validated_snapshot,
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            current_tick=159,
            evidence=ev,
        )

        for cand in res.feasible_candidates:
            # Critical path lower bound must be >= freight
            assert cand.critical_path_lower_bound_usd >= cand.freight_surcharge_usd
            # Preemptive bound must be >= critical path bound when competing bay workload exists
            assert cand.parallel_bay_lower_bound_usd >= cand.critical_path_lower_bound_usd
            # Combined lower bound is max
            assert cand.combined_lower_bound_usd == max(cand.critical_path_lower_bound_usd, cand.parallel_bay_lower_bound_usd)

    def test_pruning_gate_safely_prunes_suboptimal_branches(self, validated_snapshot: DealershipSnapshotSchema):
        engine = SourcingSearchEngine()
        ev = make_synthetic_evidence(validated_snapshot, authorize_all=True)
        
        # Set a tight best-known bound of $50.00
        # OFFER-104-S2 has usable tick 198, resulting in RO-104 finish 222 (90 weighted lateness ticks = $225 penalty)
        # Therefore, OFFER-104-S2's lower bound will easily exceed $50 and must be pruned!
        res = engine.search_sourcing_alternatives(
            snapshot=validated_snapshot,
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            current_tick=159,
            evidence=ev,
            best_known_loss_bound=Decimal("50.00"),
        )

        assert len(res.pruned_candidates) > 0
        pruned_ids = {c.offer_id for c in res.pruned_candidates}
        assert "OFFER-104-S2" in pruned_ids
        pruned_cand = next(c for c in res.pruned_candidates if c.offer_id == "OFFER-104-S2")
        assert pruned_cand.is_pruned is True
        assert "exceeds incumbent loss bound" in pruned_cand.pruning_reason

    def test_rejected_offers_on_inactive_quote(self, validated_snapshot: DealershipSnapshotSchema):
        snap_copy = validated_snapshot.model_copy(deep=True)
        # Set S2 to EXPIRED
        for o in snap_copy.supplier_offers:
            if o.offer_id == "OFFER-104-S2":
                o.quote_status = QuoteStatus.EXPIRED

        engine = SourcingSearchEngine()
        ev = make_synthetic_evidence(snap_copy, authorize_all=True)
        res = engine.search_sourcing_alternatives(
            snapshot=snap_copy,
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            current_tick=159,
            evidence=ev,
        )

        assert len(res.rejected_candidates) == 1
        assert res.rejected_candidates[0].offer_id == "OFFER-104-S2"
        assert "quote status is not ACTIVE" in res.rejected_candidates[0].rejection_reason

    def test_rejected_offers_on_expired_timestamp(self, validated_snapshot: DealershipSnapshotSchema):
        snap_copy = validated_snapshot.model_copy(deep=True)
        eval_time = datetime(2026, 11, 18, 14, 0, tzinfo=timezone.utc)
        # Set S1 valid_until to 13:00 (1 hour before evaluation time)
        for o in snap_copy.supplier_offers:
            if o.offer_id == "OFFER-104-S1":
                o.quote_valid_until = datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc)

        engine = SourcingSearchEngine()
        ev = make_synthetic_evidence(snap_copy, authorize_all=True)
        res = engine.search_sourcing_alternatives(
            snapshot=snap_copy,
            disrupted_ro_id="RO-104",
            disrupted_part_req_id="PART-REQ-104-SOLENOID",
            current_tick=159,
            evidence=ev,
            evaluation_time_utc=eval_time,
        )

        rejected_ids = {c.offer_id for c in res.rejected_candidates}
        assert "OFFER-104-S1" in rejected_ids
        rej = next(c for c in res.rejected_candidates if c.offer_id == "OFFER-104-S1")
        assert "expired at" in rej.rejection_reason
