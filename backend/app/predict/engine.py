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


@dataclass
class OperationEvidence:
    """Historical operation duration performance (actual-to-flat ratio)."""
    operation_code: str
    sample_count: int = 0
    mean_ratio: float = 1.0
    sum_squared_diffs: float = 0.0  # Welford's sum of squared differences for ratio variance

    def add_observation(self, actual_ticks: int, flat_rate_ticks: int) -> None:
        """Records an actual vs flat-rate duration observation."""
        if flat_rate_ticks <= 0:
            return
        ratio = float(actual_ticks) / float(flat_rate_ticks)
        self.sample_count += 1
        delta = ratio - self.mean_ratio
        self.mean_ratio += delta / self.sample_count
        delta2 = ratio - self.mean_ratio
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

    def get_streaming_p2_quantiles(
        self,
        supplier_id: str,
        base_usable_ready_tick: int = 0,
    ) -> Optional[QuantileInterval]:
        """Returns non-parametric streaming P² quantile estimates if available."""
        if supplier_id not in self._streaming_estimators:
            return None
        estimators = self._streaming_estimators[supplier_id]
        p10_slip = estimators["p10"].estimated_quantile
        p50_slip = estimators["p50"].estimated_quantile
        p90_slip = estimators["p90"].estimated_quantile
        p10 = max(0, min(288, int(math.floor(base_usable_ready_tick + p10_slip))))
        p50 = max(p10, min(288, int(round(base_usable_ready_tick + p50_slip))))
        p90 = max(p50, min(288, int(math.ceil(base_usable_ready_tick + p90_slip))))
        return QuantileInterval(p10=p10, p50=p50, p90=p90)

    def estimate_usable_ready_quantiles(
        self,
        base_usable_ready_tick: int,
        supplier_id: Optional[str] = None,
        min_tick_bound: int = 0,
        max_tick_bound: int = 288,
        blend_streaming_p2: bool = False,
    ) -> Tuple[QuantileInterval, CalibrationStatus]:
        """Estimates monotonic usable-ready quantiles [P10, P50, P90] in discrete ticks.
        
        Calibration Semantics:
        - UNCALIBRATED (0 observations): Quantiles reflect strictly mathematical prior
          assumptions (Gaussian prior mu_0=0, sigma_0=3 ticks), NOT empirically calibrated
          observations.
        - CALIBRATED_LIGHT (1 <= n < 10): Empirical shrinkage combining global prior and samples.
        - CALIBRATED_FULL (n >= 10): Fully sample-dominated empirical calibration.
        """
        mean_slip, std_slip, status = self.get_shrunk_posterior(supplier_id)

        # Parametric empirical-Bayes quantiles
        raw_p10 = base_usable_ready_tick + mean_slip + Z_10 * std_slip
        raw_p50 = base_usable_ready_tick + mean_slip + Z_50 * std_slip
        raw_p90 = base_usable_ready_tick + mean_slip + Z_90 * std_slip

        # If fully calibrated and blend_streaming_p2 is True, refine with P2 non-parametric estimates
        if blend_streaming_p2 and status == CalibrationStatus.CALIBRATED_FULL and supplier_id in self._streaming_estimators:
            p2_q = self.get_streaming_p2_quantiles(supplier_id, base_usable_ready_tick)
            if p2_q:
                raw_p10 = 0.5 * (raw_p10 + p2_q.p10)
                raw_p50 = 0.5 * (raw_p50 + p2_q.p50)
                raw_p90 = 0.5 * (raw_p90 + p2_q.p90)

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


class LaborDurationEstimator:
    """Empirical-Bayes shrinkage estimator for technician labor task durations.
    
    Statistical Model:
    - Global Prior on actual-to-flat duration ratio:
        rho_0 = 1.0 (on average, tasks take 100% of OEM flat-rate)
        sigma_rho_0 = 0.20 (20% standard deviation in efficiency across jobs)
        n_0 = 5.0 (prior pseudo-observation weight)
    - Group Evidence by operation_code:
        Tracked incrementally via OperationEvidence.
    - Shrinkage:
        rho_hat = (n_0 * rho_0 + n_op * r_bar) / (n_0 + n_op)
    """

    def __init__(
        self,
        prior_mean_ratio: float = 1.0,
        prior_std_ratio: float = 0.20,
        prior_weight_n0: float = 5.0,
        min_std_ratio: float = 0.05,
        calibration_threshold: int = 10,
    ):
        self.prior_mean = prior_mean_ratio
        self.prior_std = prior_std_ratio
        self.prior_variance = prior_std_ratio ** 2
        self.prior_n0 = prior_weight_n0
        self.min_std = min_std_ratio
        self.calibrated_threshold = calibration_threshold
        self._operation_evidence: Dict[str, OperationEvidence] = {}
        self._streaming_estimators: Dict[str, Dict[str, P2QuantileEstimator]] = {}

    def record_operation_duration(
        self,
        operation_code: str,
        actual_ticks: int,
        flat_rate_ticks: int,
    ) -> None:
        """Records an observed job completion to update labor duration posterior evidence."""
        if operation_code not in self._operation_evidence:
            self._operation_evidence[operation_code] = OperationEvidence(operation_code=operation_code)
            self._streaming_estimators[operation_code] = {
                "p10": P2QuantileEstimator(0.10),
                "p50": P2QuantileEstimator(0.50),
                "p90": P2QuantileEstimator(0.90),
            }
        self._operation_evidence[operation_code].add_observation(actual_ticks, flat_rate_ticks)
        if flat_rate_ticks > 0:
            ratio = float(actual_ticks) / float(flat_rate_ticks)
            for estimator in self._streaming_estimators[operation_code].values():
                estimator.add_observation(ratio)

    def get_shrunk_posterior(self, operation_code: Optional[str] = None) -> Tuple[float, float, CalibrationStatus]:
        """Calculates the shrunk posterior mean and standard deviation for an operation's labor ratio."""
        if not operation_code or operation_code not in self._operation_evidence:
            return self.prior_mean, self.prior_std, CalibrationStatus.UNCALIBRATED
        evidence = self._operation_evidence[operation_code]
        n_op = evidence.sample_count
        if n_op == 0:
            return self.prior_mean, self.prior_std, CalibrationStatus.UNCALIBRATED

        n_0 = self.prior_n0
        rho_0 = self.prior_mean
        var_0 = self.prior_variance
        r_bar = evidence.mean_ratio
        var_op = evidence.sample_variance if n_op >= 2 else var_0

        shrunk_mean = (n_0 * rho_0 + n_op * r_bar) / (n_0 + n_op)
        shrunk_variance = (
            n_0 * var_0 + (n_op - 1) * var_op + ((n_0 * n_op) / (n_0 + n_op)) * ((r_bar - rho_0) ** 2)
        ) / (n_0 + n_op)

        shrunk_std = math.sqrt(max(self.min_std ** 2, shrunk_variance))
        status = (
            CalibrationStatus.CALIBRATED_FULL
            if n_op >= self.calibrated_threshold
            else CalibrationStatus.CALIBRATED_LIGHT
        )
        return shrunk_mean, shrunk_std, status

    def estimate_duration_quantiles(
        self,
        flat_rate_ticks: int,
        operation_code: Optional[str] = None,
        min_tick: int = 1,
        max_tick: int = 288,
    ) -> Tuple[QuantileInterval, CalibrationStatus]:
        """Estimates monotonic task duration quantiles [P10, P50, P90] in discrete ticks."""
        shrunk_ratio, shrunk_std, status = self.get_shrunk_posterior(operation_code)
        raw_p10 = flat_rate_ticks * (shrunk_ratio + Z_10 * shrunk_std)
        raw_p50 = flat_rate_ticks * (shrunk_ratio + Z_50 * shrunk_std)
        raw_p90 = flat_rate_ticks * (shrunk_ratio + Z_90 * shrunk_std)

        p10 = max(min_tick, min(max_tick, int(math.floor(raw_p10))))
        p50 = max(p10, min(max_tick, int(round(raw_p50))))
        p90 = max(p50, min(max_tick, int(math.ceil(raw_p90))))
        return QuantileInterval(p10=p10, p50=p50, p90=p90), status
