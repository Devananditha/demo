"""Unit and Golden Fixture Tests for Four-State Readiness Classifier."""

from datetime import datetime, timedelta, timezone
import pytest

from app.data.loader import load_fixture_data
from app.predict.classifier import PredictReadinessClassifier
from app.predict.engine import EmpiricalBayesQuantileEngine
from app.predict.models import CalibrationStatus, ReadinessState
from app.schemas.domain import ROStatus, VehiclePhysicalState


@pytest.fixture
def snapshot():
    """Loads validated S-MATH-01 synthetic snapshot."""
    return load_fixture_data()


@pytest.fixture
def classifier():
    """Instantiates the PredictReadinessClassifier."""
    return PredictReadinessClassifier()


class TestPredictFourStateClassifier:
    def test_s_math_01_golden_fixture_evaluations(self, classifier, snapshot):
        """Mandatory Golden Evaluation: Evaluates all 6 ROs in S-MATH-01.
        
        Anchors:
          RO-104 MUST be classified AT_RISK.
          RO-105 MUST be classified BLOCKED.
        """
        # Freeze reference evaluation time to fixture time (2026-11-18 13:15:00 UTC)
        ref_time = datetime(2026, 11, 18, 13, 15, 0, tzinfo=timezone.utc)
        report = classifier.assess_dealership_readiness(snapshot, current_tick=159, now_utc=ref_time)

        assessments_by_id = {a.ro_id: a for a in report.assessments}
        assert len(assessments_by_id) == 6

        # RO-101: Brake job, parts in stock, positive slack (+150m) -> READY
        ro_101 = assessments_by_id["RO-101"]
        assert ro_101.state == ReadinessState.READY
        assert ro_101.slack.slack_minutes > 30

        # RO-102: Express maintenance, parts in stock, positive slack (+120m) -> READY
        ro_102 = assessments_by_id["RO-102"]
        assert ro_102.state == ReadinessState.READY
        assert ro_102.slack.slack_minutes > 30

        # RO-103: Suspension, parts in stock, positive slack (+300m) -> READY
        ro_103 = assessments_by_id["RO-103"]
        assert ro_103.state == ReadinessState.READY
        assert ro_103.slack.slack_minutes > 30

        # RO-104 (MANDATORY ANCHOR): Transmission solenoid delayed in transit,
        # immobilized on lift, alternative Hotshot offer S1 available -> AT_RISK
        ro_104 = assessments_by_id["RO-104"]
        assert ro_104.state == ReadinessState.AT_RISK
        assert "VEHICLE_IMMOBILIZED_ON_LIFT_STALLED" in ro_104.reasons or "PARTS_IN_TRANSIT_LEAD_TIME_RISK" in ro_104.reasons

        # RO-105 (MANDATORY ANCHOR): Inverter harness BACKORDERED without ETA or quotes -> BLOCKED
        ro_105 = assessments_by_id["RO-105"]
        assert ro_105.state == ReadinessState.BLOCKED
        assert "PART_BACKORDERED_NO_ETA" in ro_105.reasons

        # RO-106: Stalling diagnosis, no parts required, positive slack (+390m) -> READY
        ro_106 = assessments_by_id["RO-106"]
        assert ro_106.state == ReadinessState.READY

        # Summary count assertions
        assert report.summary_counts[ReadinessState.READY.value] == 4
        assert report.summary_counts[ReadinessState.AT_RISK.value] == 1
        assert report.summary_counts[ReadinessState.BLOCKED.value] == 1

    def test_unknown_state_on_stale_telemetry(self, classifier, snapshot):
        """Precedence: Stale telemetry fails closed into UNKNOWN."""
        ro = snapshot.repair_orders[0].model_copy(deep=True)
        # Set updated_at to 48 hours in the past (> 24 hour threshold)
        now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
        ro.updated_at = now - timedelta(hours=48)

        assessment = classifier.assess_repair_order(ro, snapshot, now_utc=now)
        assert assessment.state == ReadinessState.UNKNOWN
        assert "STALE_TELEMETRY_DATA" in assessment.reasons

    def test_unknown_state_on_missing_critical_telemetry(self, classifier, snapshot):
        """Precedence: Unknown vehicle physical state fails closed into UNKNOWN."""
        ro = snapshot.repair_orders[0].model_copy(deep=True)
        ro.physical_state = VehiclePhysicalState.UNKNOWN

        assessment = classifier.assess_repair_order(ro, snapshot)
        assert assessment.state == ReadinessState.UNKNOWN
        assert "UNKNOWN_VEHICLE_PHYSICAL_STATE" in assessment.reasons

    def test_blocked_state_on_unsupported_technician_skill(self, classifier, snapshot):
        """Hard Gate: If rooftop has no active technician with required skill, marks BLOCKED."""
        ro = snapshot.repair_orders[0].model_copy(deep=True)
        # Modify snapshot tasks so task requires EV_CERTIFIED, but deactivate EV techs
        snap_copy = snapshot.model_copy(deep=True)
        for tech in snap_copy.technicians:
            tech.skill_certifications = ["GENERAL_MAINTENANCE"]  # Strip all skills

        assessment = classifier.assess_repair_order(ro, snap_copy)
        assert assessment.state == ReadinessState.BLOCKED
        assert any("UNAVAILABLE_TECHNICIAN_SKILL" in r for r in assessment.reasons)

    def test_blocked_state_on_unsupported_bay_type(self, classifier, snapshot):
        """Hard Gate: If rooftop has no operational bay of required type, marks BLOCKED."""
        snap_copy = snapshot.model_copy(deep=True)
        for bay in snap_copy.bays:
            bay.is_operational = False  # Deactivate all bays

        ro = snap_copy.repair_orders[0]
        assessment = classifier.assess_repair_order(ro, snap_copy)
        assert assessment.state == ReadinessState.BLOCKED
        assert any("UNAVAILABLE_BAY_TYPE" in r for r in assessment.reasons)

    def test_at_risk_state_on_tight_slack_under_30_minutes(self, classifier, snapshot):
        """AT_RISK Gate: Triggers when operational slack drops below 30 minutes (6 ticks)."""
        ro = snapshot.repair_orders[0].model_copy(deep=True)
        snap_copy = snapshot.model_copy(deep=True)
        # Task 101 duration = 18 ticks.
        # Set promise tick to 118 -> LFS = 118 - 18 = 100.
        # Usable ready tick is 96. Slack = 100 - 96 = 4 ticks = 20 minutes (< 30m).
        ro.promise_tick = 118

        assessment = classifier.assess_repair_order(ro, snap_copy)
        assert assessment.state == ReadinessState.AT_RISK
        assert "SLACK_BELOW_30_MINUTES" in assessment.reasons

    def test_at_risk_state_on_high_delay_probability(self, snapshot):
        """AT_RISK Gate: Triggers when P(delay) exceeds tau_raise (0.25)."""
        # Create an engine with high supplier variance
        engine = EmpiricalBayesQuantileEngine(prior_mean_slip_ticks=5.0, prior_std_slip_ticks=6.0)
        custom_classifier = PredictReadinessClassifier(quantile_engine=engine, tau_raise=0.25)

        ro = snapshot.repair_orders[0].model_copy(deep=True)
        snap_copy = snapshot.model_copy(deep=True)
        # Task 101 duration = 18 ticks.
        # Set promise tick to 122 -> LFS = 122 - 18 = 104.
        # With base usable tick 96 + mean slip 5.0 = 101, std = 6.0:
        # z = (104 - 101)/6 = 0.5 -> P(delay) = 1 - Phi(0.5) = 0.3085 > 0.25!
        ro.promise_tick = 122

        assessment = custom_classifier.assess_repair_order(ro, snap_copy)
        assert assessment.state == ReadinessState.AT_RISK
        assert any("DELAY_PROBABILITY_EXCEEDS_THRESHOLD" in r for r in assessment.reasons)
