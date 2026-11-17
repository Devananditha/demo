"""Empirical-Bayes Quantile Engine for Predictive Service Readiness (Layer 1).

Authoritative Reference:
- docs/03_PRODUCT_REQUIREMENTS.md (Section 2.3: Layer 1 Deterministic Baseline)
- Technical Report Section 6.1 (Module 1: Predict)
- Jain & Chlamtac (1985): "The P² Algorithm for Dynamic Quantile Computation"

Guarantees:
1. Strict quantile monotonicity: P10 <= P50 <= P90.
2. Deterministic empirical-Bayes shrinkage combining global priors with group evidence.
3. Robust cold-start operation returning UNCALIBRATED without crashing.
4. Mathematically consistent delay probability P(delay) = P(usable_ready > LFS).
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.predict.models import CalibrationStatus, QuantileInterval


# Standard normal quantile coefficients (Z-scores)
Z_10: float = -1.2815515655446004
Z_50: float = 0.0
Z_90: float = 1.2815515655446004


def standard_normal_cdf(x: float) -> float:
    """Computes standard normal cumulative distribution function Phi(x) using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class SupplierEvidence:
    """Historical supplier delivery performance statistics."""
    supplier_id: str
    sample_count: int = 0
    mean_slip_ticks: float = 0.0
    sum_squared_diffs: float = 0.0  # Welford's sum of squared differences for sample variance

    def add_observation(self, slip_ticks: float) -> None:
        """Incrementally updates sample mean and variance using Welford's online algorithm."""
        self.sample_count += 1
        delta = slip_ticks - self.mean_slip_ticks
        self.mean_slip_ticks += delta / self.sample_count
        delta2 = slip_ticks - self.mean_slip_ticks
        self.sum_squared_diffs += delta * delta2

    @property
    def sample_variance(self) -> float:
        if self.sample_count < 2:
            return 0.0
        return self.sum_squared_diffs / (self.sample_count - 1)


class P2QuantileEstimator:
    """The P² (Piecewise-Parabolic) algorithm for online streaming quantile estimation.
    
    Maintains 5 dynamic markers to track a single quantile p without storing historical samples.
    """

    def __init__(self, p: float):
        if not (0.0 < p < 1.0):
            raise ValueError(f"Quantile probability p must be in (0, 1), got {p}")
        self.p = p
        self.count: int = 0
        self.q: List[float] = []  # Marker heights (values)
        self.n: List[int] = []    # Actual marker positions
        self.n_prime: List[float] = []  # Desired marker positions
        self.dn_prime: List[float] = [0.0, p / 2.0, p, (1.0 + p) / 2.0, 1.0]

    def add_observation(self, x: float) -> None:
        """Adds a new scalar observation and updates dynamic markers."""
        if self.count < 5:
            self.q.append(x)
            self.count += 1
            if self.count == 5:
                self.q.sort()
                self.n = [1, 2, 3, 4, 5]
                self.n_prime = [1.0, 1.0 + 2.0 * self.p, 1.0 + 4.0 * self.p, 3.0 + 2.0 * self.p, 5.0]
            return

        # Find cell k such that q[k] <= x < q[k+1]
        if x < self.q[0]:
            self.q[0] = x
            k = 0
        elif x >= self.q[4]:
            self.q[4] = x
            k = 3
        else:
            k = 0
            for i in range(4):
                if self.q[i] <= x < self.q[i + 1]:
                    k = i
                    break

        # Increment actual positions for markers k+1 through 4
        for i in range(k + 1, 5):
            self.n[i] += 1

        # Update desired positions
        for i in range(5):
            self.n_prime[i] += self.dn_prime[i]

        # Adjust marker heights using piecewise parabolic or linear formula
        for i in range(1, 4):
            d = self.n_prime[i] - self.n[i]
            if (d >= 1.0 and (self.n[i + 1] - self.n[i]) > 1) or (d <= -1.0 and (self.n[i - 1] - self.n[i]) < -1):
                d_sign = 1 if d > 0 else -1
                # Try parabolic formula
                q_adj = self._parabolic(i, d_sign)
                if self.q[i - 1] < q_adj < self.q[i + 1]:
                    self.q[i] = q_adj
                else:
                    # Fallback to linear
                    self.q[i] = self._linear(i, d_sign)
                self.n[i] += d_sign

    def _parabolic(self, i: int, d: int) -> float:
        n, q = self.n, self.q
        term1 = d / float(n[i + 1] - n[i - 1])
        term2 = (n[i] - n[i - 1] + d) * (q[i + 1] - q[i]) / float(n[i + 1] - n[i])
        term3 = (n[i + 1] - n[i] - d) * (q[i] - q[i - 1]) / float(n[i] - n[i - 1])
        return q[i] + term1 * (term2 + term3)

    def _linear(self, i: int, d: int) -> float:
        return self.q[i] + d * (self.q[i + d] - self.q[i]) / float(self.n[i + d] - self.n[i])

    @property
    def estimated_quantile(self) -> float:
        """Returns the current quantile estimate."""
        if self.count == 0:
            return 0.0
        if self.count < 5:
            sorted_q = sorted(self.q)
            idx = int(round(self.p * (self.count - 1)))
            return sorted_q[idx]
        return self.q[2]


class EmpiricalBayesQuantileEngine:
    """Predictive Lead-Time & Usable-Ready Distribution Estimator.
    
    Statistical Model:
    - Global Prior on delivery slip (ticks):
        mu_0 = 0.0 (quoted ETA is unbiased on average)
        sigma_0 = 3.0 ticks (15 min standard deviation)
        n_0 = 5 (prior pseudo-observation weight)
    - Group Evidence:
        Tracked by supplier_id.
    - Shrinkage:
        mu_hat_s = (n_0 * mu_0 + n_s * x_bar_s) / (n_0 + n_s)
        sigma_hat_s = sqrt(shrunk variance)
    """

    def __init__(
        self,
        prior_mean_slip_ticks: float = 0.0,
        prior_std_slip_ticks: float = 3.0,
        prior_weight_n0: float = 5.0,
        min_std_ticks: float = 0.5,
        calibration_threshold_full: int = 10,
    ):
        self.prior_mean = prior_mean_slip_ticks
        self.prior_std = prior_std_slip_ticks
        self.prior_variance = prior_std_slip_ticks ** 2
        self.prior_n0 = prior_weight_n0
        self.min_std = min_std_ticks
        self.calibrated_threshold = calibration_threshold_full

        # Supplier evidence store: supplier_id -> SupplierEvidence
        self._supplier_evidence: Dict[str, SupplierEvidence] = {}
        # Streaming P2 quantile estimators for empirical verification
        self._streaming_estimators: Dict[str, Dict[str, P2QuantileEstimator]] = {}

    def record_supplier_delivery(
        self,
        supplier_id: str,
        actual_usable_tick: int,
        quoted_usable_tick: int,
    ) -> None:
        """Records an observed delivery to update empirical-Bayes posterior evidence."""
        slip_ticks = float(actual_usable_tick - quoted_usable_tick)
        if supplier_id not in self._supplier_evidence:
            self._supplier_evidence[supplier_id] = SupplierEvidence(supplier_id=supplier_id)
            self._streaming_estimators[supplier_id] = {
                "p10": P2QuantileEstimator(0.10),
                "p50": P2QuantileEstimator(0.50),
                "p90": P2QuantileEstimator(0.90),
            }

        self._supplier_evidence[supplier_id].add_observation(slip_ticks)
        for estimator in self._streaming_estimators[supplier_id].values():
            estimator.add_observation(slip_ticks)

    def get_shrunk_posterior(self, supplier_id: Optional[str] = None) -> Tuple[float, float, CalibrationStatus]:
        """Calculates the shrunk posterior mean and standard deviation for a supplier.
        
        Returns:
            Tuple of (posterior_mean_slip, posterior_std_slip, calibration_status).
        """
        if not supplier_id or supplier_id not in self._supplier_evidence:
            # Pure cold-start: return prior
            return self.prior_mean, self.prior_std, CalibrationStatus.UNCALIBRATED

        evidence = self._supplier_evidence[supplier_id]
        n_s = evidence.sample_count
        if n_s == 0:
            return self.prior_mean, self.prior_std, CalibrationStatus.UNCALIBRATED

        n_0 = self.prior_n0
        mu_0 = self.prior_mean
        var_0 = self.prior_variance

        x_bar = evidence.mean_slip_ticks
        var_s = evidence.sample_variance if n_s >= 2 else var_0

        # Empirical-Bayes mean shrinkage
        shrunk_mean = (n_0 * mu_0 + n_s * x_bar) / (n_0 + n_s)

        # Empirical-Bayes pooled variance shrinkage
        shrunk_variance = (
            n_0 * var_0 + (n_s - 1) * var_s + ((n_0 * n_s) / (n_0 + n_s)) * ((x_bar - mu_0) ** 2)
        ) / (n_0 + n_s)

        shrunk_std = math.sqrt(max(self.min_std ** 2, shrunk_variance))
        status = (
            CalibrationStatus.CALIBRATED_FULL
            if n_s >= self.calibrated_threshold
            else CalibrationStatus.CALIBRATED_LIGHT
        )
        return shrunk_mean, shrunk_std, status

    def estimate_usable_ready_quantiles(
        self,
        base_usable_ready_tick: int,
        supplier_id: Optional[str] = None,
        min_tick_bound: int = 0,
        max_tick_bound: int = 288,
    ) -> Tuple[QuantileInterval, CalibrationStatus]:
        """Estimates monotonic usable-ready quantiles [P10, P50, P90] in discrete ticks."""
        mean_slip, std_slip, status = self.get_shrunk_posterior(supplier_id)

        # Parametric empirical-Bayes quantiles
        raw_p10 = base_usable_ready_tick + mean_slip + Z_10 * std_slip
        raw_p50 = base_usable_ready_tick + mean_slip + Z_50 * std_slip
        raw_p90 = base_usable_ready_tick + mean_slip + Z_90 * std_slip

        # Enforce bounds and monotonicity
        p10 = max(min_tick_bound, min(max_tick_bound, int(math.floor(raw_p10))))
        p50 = max(p10, min(max_tick_bound, int(round(raw_p50))))
        p90 = max(p50, min(max_tick_bound, int(math.ceil(raw_p90))))

        return QuantileInterval(p10=p10, p50=p50, p90=p90), status

    def compute_delay_probability(
        self,
        base_usable_ready_tick: int,
        latest_feasible_start_tick: int,
        supplier_id: Optional[str] = None,
    ) -> float:
        """Computes exact P(delay) = P(usable_ready > latest_feasible_start) under predictive distribution."""
        mean_slip, std_slip, _ = self.get_shrunk_posterior(supplier_id)
        expected_usable = base_usable_ready_tick + mean_slip

        if std_slip <= 1e-6:
            return 1.0 if expected_usable > latest_feasible_start_tick else 0.0

        # Z-score for latest feasible start
        z = (latest_feasible_start_tick - expected_usable) / std_slip
        # P(delay) = 1 - Phi(z)
        p_delay = 1.0 - standard_normal_cdf(z)
        # Bound cleanly within [0.0, 1.0]
        return max(0.0, min(1.0, float(round(p_delay, 4))))
