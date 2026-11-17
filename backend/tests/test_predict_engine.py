"""Unit Tests for Empirical-Bayes Quantile Engine (Layer 1)."""

import pytest

from app.predict.engine import (
    EmpiricalBayesQuantileEngine,
    P2QuantileEstimator,
    SupplierEvidence,
    standard_normal_cdf,
)
from app.predict.models import CalibrationStatus, QuantileInterval


class TestP2QuantileEstimator:
    def test_invalid_probability_raises(self):
        with pytest.raises(ValueError, match="Quantile probability p must be in"):
            P2QuantileEstimator(0.0)
        with pytest.raises(ValueError, match="Quantile probability p must be in"):
            P2QuantileEstimator(1.0)

    def test_p2_small_sample_tracking(self):
        estimator = P2QuantileEstimator(0.5)
        samples = [10.0, 20.0, 30.0]
        for s in samples:
            estimator.add_observation(s)
        # For 3 samples, median of [10, 20, 30] is 20.0
        assert estimator.estimated_quantile == 20.0

    def test_p2_streaming_gaussian_quantiles(self):
        estimator_50 = P2QuantileEstimator(0.50)
        estimator_90 = P2QuantileEstimator(0.90)
        # Feed 100 sorted or unsorted values from uniform range [0, 100]
        for val in range(101):
            estimator_50.add_observation(float(val))
            estimator_90.add_observation(float(val))

        # P50 should be close to 50
        assert 45.0 <= estimator_50.estimated_quantile <= 55.0
        # P90 should be close to 90
        assert 80.0 <= estimator_90.estimated_quantile <= 95.0


class TestEmpiricalBayesQuantileEngine:
    def test_cold_start_uncalibrated(self):
        engine = EmpiricalBayesQuantileEngine()
        quantiles, status = engine.estimate_usable_ready_quantiles(
            base_usable_ready_tick=165,
            supplier_id="UNKNOWN_SUPPLIER",
        )
        assert status == CalibrationStatus.UNCALIBRATED
        assert quantiles.p10 <= quantiles.p50 <= quantiles.p90
        # With prior mean 0 and std 3.0, p50 should equal base tick 165
        assert quantiles.p50 == 165

    def test_quantile_monotonicity_guaranteed(self):
        engine = EmpiricalBayesQuantileEngine()
        for base in [0, 50, 100, 165, 204, 288]:
            q, _ = engine.estimate_usable_ready_quantiles(base, "SUPP_1")
            assert q.p10 <= q.p50 <= q.p90
            assert 0 <= q.p10 <= 288
            assert 0 <= q.p90 <= 288

    def test_empirical_bayes_shrinkage_with_observations(self):
        engine = EmpiricalBayesQuantileEngine(
            prior_mean_slip_ticks=0.0,
            prior_std_slip_ticks=3.0,
            prior_weight_n0=5.0,
        )
        # Supplier S1 consistently arrives 6 ticks late (30 mins late)
        for _ in range(5):
            engine.record_supplier_delivery(
                supplier_id="S1_HOTSHOT",
                actual_usable_tick=171,
                quoted_usable_tick=165,
            )

        mean_slip, std_slip, status = engine.get_shrunk_posterior("S1_HOTSHOT")
        assert status == CalibrationStatus.CALIBRATED_LIGHT
        # With n0=5, mu0=0 and n=5, x_bar=6: shrunk mean = (5*0 + 5*6)/10 = 3.0 ticks!
        assert round(mean_slip, 2) == 3.0

        # Now add 15 more observations (total 20 >= 10) -> CALIBRATED_FULL
        for _ in range(15):
            engine.record_supplier_delivery(
                supplier_id="S1_HOTSHOT",
                actual_usable_tick=171,
                quoted_usable_tick=165,
            )

        _, _, full_status = engine.get_shrunk_posterior("S1_HOTSHOT")
        assert full_status == CalibrationStatus.CALIBRATED_FULL

    def test_delay_probability_consistency(self):
        engine = EmpiricalBayesQuantileEngine()
        # Case 1: LFS is far into the future (tick 250) vs base 165 -> P(delay) near 0.0
        p_delay_low = engine.compute_delay_probability(
            base_usable_ready_tick=165,
            latest_feasible_start_tick=250,
        )
        assert p_delay_low < 0.01

        # Case 2: LFS is exactly equal to expected usable ready (165) -> P(delay) is approx 0.50
        p_delay_mid = engine.compute_delay_probability(
            base_usable_ready_tick=165,
            latest_feasible_start_tick=165,
        )
        assert 0.45 <= p_delay_mid <= 0.55

        # Case 3: LFS is earlier than base usable ready (tick 150 < 165) -> P(delay) near 1.0
        p_delay_high = engine.compute_delay_probability(
            base_usable_ready_tick=165,
            latest_feasible_start_tick=150,
        )
        assert p_delay_high > 0.99

    def test_deterministic_reproducibility(self):
        engine1 = EmpiricalBayesQuantileEngine()
        engine2 = EmpiricalBayesQuantileEngine()

        q1, _ = engine1.estimate_usable_ready_quantiles(180, "SUPP_X")
        q2, _ = engine2.estimate_usable_ready_quantiles(180, "SUPP_X")

        assert q1.p10 == q2.p10
        assert q1.p50 == q2.p50
        assert q1.p90 == q2.p90

    def test_streaming_p2_quantiles_retrieval_and_blending(self):
        """Finding 4: Streaming P² quantiles can be retrieved and blended with empirical Bayes."""
        engine = EmpiricalBayesQuantileEngine()
        # Record 15 delivery slip observations
        for i in range(15):
            engine.record_supplier_delivery("S1", actual_usable_tick=105 + (i % 5), quoted_usable_tick=100)

        # Retrieve direct streaming P2 quantiles
        p2_q = engine.get_streaming_p2_quantiles("S1", base_usable_ready_tick=100)
        assert p2_q is not None
        assert p2_q.p10 <= p2_q.p50 <= p2_q.p90

        # Estimate with blending enabled
        blended_q, status = engine.estimate_usable_ready_quantiles(
            base_usable_ready_tick=100,
            supplier_id="S1",
            blend_streaming_p2=True,
        )
        assert status == CalibrationStatus.CALIBRATED_FULL
        assert blended_q.p10 <= blended_q.p50 <= blended_q.p90


class TestLaborDurationEstimator:
    """Finding 4: Verification of labor operation duration empirical-Bayes estimation."""

    def test_labor_duration_cold_start(self):
        from app.predict.engine import LaborDurationEstimator
        estimator = LaborDurationEstimator()
        q, status = estimator.estimate_duration_quantiles(flat_rate_ticks=12, operation_code="OP-BRAKE")
        assert status == CalibrationStatus.UNCALIBRATED
        assert q.p10 <= q.p50 <= q.p90
        # Under cold start prior (mean ratio 1.0), P50 is approx 12 ticks
        assert q.p50 == 12

    def test_labor_duration_shrinkage_with_observations(self):
        from app.predict.engine import LaborDurationEstimator
        estimator = LaborDurationEstimator()
        # Record 4 slow jobs (ratio = 15/10 = 1.5)
        for _ in range(4):
            estimator.record_operation_duration("OP-SLOW", actual_ticks=15, flat_rate_ticks=10)

        ratio, _, status = estimator.get_shrunk_posterior("OP-SLOW")
        assert status == CalibrationStatus.CALIBRATED_LIGHT
        # Prior is 1.0 (weight 5), sample mean is 1.5 (weight 4) -> shrunk mean = (5*1.0 + 4*1.5)/9 = 11/9 = 1.22
        assert 1.15 < ratio < 1.30

        # Add 8 more observations -> total 12 -> CALIBRATED_FULL
        for _ in range(8):
            estimator.record_operation_duration("OP-SLOW", actual_ticks=15, flat_rate_ticks=10)

        ratio_full, _, status_full = estimator.get_shrunk_posterior("OP-SLOW")
        assert status_full == CalibrationStatus.CALIBRATED_FULL
        assert ratio_full > ratio  # Pulled even closer to 1.5
