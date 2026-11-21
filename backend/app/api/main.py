"""FastAPI Application for ServiceYield AI Decision Intelligence & Optimisation Telemetry.

Authoritative Reference:
- docs/00_EXECUTIVE_PRODUCT_OVERVIEW.md
- docs/04_EXACT_NOVELTY_AND_SHADOW_PRICE.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md
- docs/12_VERIFICATION_AND_REVALIDATION.md
- PROJECT_RULES.md
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.authority.commit import AuthorityCommitGateway
from app.authority.models import CommitRequest, CommitResult, ManagerRecoveryApproval
from app.data.loader import load_canonical_evidence, load_fixture_data
from app.optimise.config import OptimiseConfig
from app.optimise.cpsat_solver import CPSATScheduler
from app.optimise.models import BayHourShadowPrice, ScheduleResult
from app.optimise.shadow_price import BayHourShadowPriceCalculator
from app.predict.classifier import PredictReadinessClassifier
from app.predict.models import DealershipReadinessReport
from app.recover.models import (
    DisruptionEvent,
    DisruptionType,
    RecoveryRecommendationReport,
)
from app.recover.replan import RecoveryReplanningPipeline
from app.replay.engine import replay_engine
from app.replay.models import DecisionReplayRecord
from app.schemas.domain import EconomicParametersSchema
from app.verifier.models import CandidateSchedulePlan, VerificationResult
from app.verifier.sweep_oracle import SweepLineOracle

# Reference Evaluation Timestamp for S-MATH-01 Fixture
REFERENCE_EVAL_TIME_UTC = datetime(2026, 11, 18, 13, 15, 0, tzinfo=timezone.utc)
REFERENCE_CURRENT_TICK = 159

app = FastAPI(
    title="ServiceYield AI — Decision Intelligence & Optimisation API",
    version="0.2.0",
    description="Event-driven dealership service-bay optimisation, recovery replanning, and verification telemetry service.",
)

# CORS configuration restricted to local frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST & RESPONSE SCHEMAS
# ============================================================================

class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = "ok"


class RepairOrderStateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ro_id: str
    status: str
    physical_state: str
    assigned_bay_id: Optional[str] = None
    promise_tick: int


class DealershipStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rooftop_id: str
    snapshot_hash: str
    evaluation_tick: int = REFERENCE_CURRENT_TICK
    operating_day_end_tick: int
    overtime_cutoff_tick: int
    repair_orders: List[RepairOrderStateItem]


class ReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rooftop_id: str = Field(..., min_length=1, description="Target dealership rooftop identifier")
    snapshot_hash: str = Field(..., min_length=1, description="Expected snapshot SHA-256 hash")


class OptimiseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rooftop_id: str = Field(..., min_length=1, description="Target dealership rooftop identifier")
    snapshot_hash: str = Field(..., min_length=1, description="Expected snapshot SHA-256 hash")
    allow_emergency_overtime: bool = Field(default=False, description="Authorize dispatch beyond technician shift end")
    time_budget_seconds: float = Field(default=2.5, gt=0.0, le=30.0, description="Solver execution time limit")
    economic_parameters: Optional[EconomicParametersSchema] = Field(default=None, description="Optional override of economic parameters")


class ShadowPriceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rooftop_id: str = Field(..., min_length=1, description="Target dealership rooftop identifier")
    snapshot_hash: str = Field(..., min_length=1, description="Expected snapshot SHA-256 hash")
    bay_id: str = Field(..., min_length=1, description="Target service bay identifier for shadow price calculation")
    start_tick: int = Field(default=159, ge=0, le=288, description="Evaluation window start tick (default: 1:15 PM)")
    end_tick: int = Field(default=171, ge=0, le=288, description="Evaluation window end tick (default: 2:15 PM, 1 hour)")
    economic_parameters: Optional[EconomicParametersSchema] = Field(default=None, description="Optional economic parameters")


class RecoveryReplanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rooftop_id: str = Field(..., min_length=1, description="Target dealership rooftop identifier")
    snapshot_hash: str = Field(..., min_length=1, description="Expected snapshot SHA-256 hash")
    disrupted_ro_id: Optional[str] = Field(default="RO-104", description="Anchor disrupted repair order")
    disrupted_part_req_id: Optional[str] = Field(default="PART-REQ-104-SOLENOID", description="Affected part requirement")
    trigger_tick: Optional[int] = Field(default=159, ge=0, le=288, description="Evaluation/disruption tick")
    primary_supplier_delay_minutes: Optional[int] = Field(default=180, ge=0, description="Reported supplier delay in minutes")
    allow_emergency_overtime: bool = Field(default=True, description="Authorize overtime to complete reassembly")
    economic_parameters: Optional[EconomicParametersSchema] = Field(default=None, description="Configured economic parameters")


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rooftop_id: str = Field(..., min_length=1, description="Target dealership rooftop identifier")
    snapshot_hash: str = Field(..., min_length=1, description="Expected snapshot SHA-256 hash")
    plan: CandidateSchedulePlan = Field(..., description="Candidate schedule plan to independently audit")


# Authority commit gateway singleton
_authority_gateway = AuthorityCommitGateway()


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/api/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def get_health() -> HealthResponse:
    """Service health probe endpoint."""
    return HealthResponse(status="ok")


@app.get("/api/v1/state", response_model=DealershipStateResponse, status_code=status.HTTP_200_OK)
def get_canonical_state() -> DealershipStateResponse:
    """Loads and returns canonical workshop state from S-MATH-01 fixture."""
    snapshot = load_fixture_data()

    ro_items = [
        RepairOrderStateItem(
            ro_id=ro.ro_id,
            status=ro.status.value if hasattr(ro.status, "value") else str(ro.status),
            physical_state=ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state),
            assigned_bay_id=ro.assigned_bay_id,
            promise_tick=ro.promise_tick,
        )
        for ro in snapshot.repair_orders
    ]

    return DealershipStateResponse(
        rooftop_id=snapshot.rooftop.rooftop_id,
        snapshot_hash=snapshot.snapshot_hash or "",
        evaluation_tick=REFERENCE_CURRENT_TICK,
        operating_day_end_tick=snapshot.rooftop.operating_day_end_tick,
        overtime_cutoff_tick=snapshot.rooftop.overtime_cutoff_tick,
        repair_orders=ro_items,
    )


@app.post(
    "/api/v1/predict/readiness",
    response_model=DealershipReadinessReport,
    status_code=status.HTTP_200_OK,
)
def predict_readiness(request: ReadinessRequest) -> DealershipReadinessReport:
    """Calculates Layer 1 Empirical-Bayes readiness classifications for all active ROs."""
    snapshot = load_fixture_data()

    if request.rooftop_id != snapshot.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    if request.snapshot_hash != snapshot.snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stale snapshot hash: expected '{snapshot.snapshot_hash}', received '{request.snapshot_hash}'.",
        )

    classifier = PredictReadinessClassifier()
    report = classifier.assess_dealership_readiness(
        snapshot,
        current_tick=REFERENCE_CURRENT_TICK,
        now_utc=REFERENCE_EVAL_TIME_UTC,
    )

    return report


@app.post(
    "/api/v1/optimise/schedule",
    response_model=ScheduleResult,
    status_code=status.HTTP_200_OK,
)
def optimise_schedule(request: OptimiseRequest) -> ScheduleResult:
    """Solves the discrete workshop scheduling problem using OR-Tools CP-SAT with dual verification."""
    snapshot = load_fixture_data()

    if request.rooftop_id != snapshot.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    if request.snapshot_hash != snapshot.snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stale snapshot hash: expected '{snapshot.snapshot_hash}', received '{request.snapshot_hash}'.",
        )

    config = OptimiseConfig.from_economic_parameters(
        request.economic_parameters,
        allow_emergency_overtime=request.allow_emergency_overtime,
        time_budget_seconds=request.time_budget_seconds,
    )
    ev = load_canonical_evidence(snapshot, current_tick=REFERENCE_CURRENT_TICK)
    scheduler = CPSATScheduler(config=config)
    result = scheduler.schedule(
        snapshot=snapshot,
        plan_id=f"PLAN-API-{snapshot.rooftop.rooftop_id}",
        evidence=ev,
    )

    return result


@app.post(
    "/api/v1/optimise/shadow-price",
    response_model=BayHourShadowPrice,
    status_code=status.HTTP_200_OK,
)
def calculate_shadow_price(request: ShadowPriceRequest) -> BayHourShadowPrice:
    """Estimates the marginal economic value nu_b(t) of bay capacity via discrete sensitivity re-solves."""
    snapshot = load_fixture_data()

    if request.rooftop_id != snapshot.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    if request.snapshot_hash != snapshot.snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stale snapshot hash: expected '{snapshot.snapshot_hash}', received '{request.snapshot_hash}'.",
        )

    if request.start_tick >= request.end_tick:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"start_tick ({request.start_tick}) must be strictly less than end_tick ({request.end_tick}).",
        )

    config = OptimiseConfig.from_economic_parameters(request.economic_parameters)
    ev = load_canonical_evidence(snapshot, current_tick=REFERENCE_CURRENT_TICK)
    calculator = BayHourShadowPriceCalculator(config=config)
    shadow_price = calculator.calculate_shadow_price(
        snapshot=snapshot,
        bay_id=request.bay_id,
        start_tick=request.start_tick,
        end_tick=request.end_tick,
        evidence=ev,
    )

    return shadow_price


@app.post(
    "/api/v1/recover/replan",
    response_model=RecoveryRecommendationReport,
    status_code=status.HTTP_200_OK,
)
def recover_replan(request: RecoveryReplanRequest) -> RecoveryRecommendationReport:
    """Executes full-shop recovery replanning, Pareto sourcing evaluation, and Decision Replay delta calculation."""
    snapshot = load_fixture_data()

    if request.rooftop_id != snapshot.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    if request.snapshot_hash != snapshot.snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stale snapshot hash: expected '{snapshot.snapshot_hash}', received '{request.snapshot_hash}'.",
        )

    disruption = DisruptionEvent(
        disrupted_ro_id=request.disrupted_ro_id or "RO-104",
        disrupted_part_req_id=request.disrupted_part_req_id or "PART-REQ-104-SOLENOID",
        disruption_type=DisruptionType.PARTS_DELAY,
        trigger_tick=request.trigger_tick or REFERENCE_CURRENT_TICK,
        primary_supplier_delay_minutes=request.primary_supplier_delay_minutes or 180,
        delayed_ready_tick=198,
        description=f"Supplier primary ground transit delayed {request.primary_supplier_delay_minutes} min to tick 198",
        event_timestamp_utc=REFERENCE_EVAL_TIME_UTC,
    )

    config = OptimiseConfig.from_economic_parameters(
        request.economic_parameters,
        allow_emergency_overtime=request.allow_emergency_overtime,
    )
    ev = load_canonical_evidence(snapshot, current_tick=request.trigger_tick or REFERENCE_CURRENT_TICK)
    pipeline = RecoveryReplanningPipeline(config=config)
    report = pipeline.execute_recovery(
        snapshot=snapshot,
        disruption_event=disruption,
        evidence=ev,
        evaluation_time_utc=REFERENCE_EVAL_TIME_UTC,
    )

    return report


@app.post(
    "/api/v1/verifier/verify",
    response_model=VerificationResult,
    status_code=status.HTTP_200_OK,
)
def verify_candidate_schedule(request: VerificationRequest) -> VerificationResult:
    """Independently audits a candidate schedule plan using the O(N log N) Sweep-Line Oracle."""
    snapshot = load_fixture_data()

    if request.rooftop_id != snapshot.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    oracle = SweepLineOracle(snapshot)
    verdict = oracle.verify_plan(request.plan)
    return verdict


@app.get(
    "/api/v1/replay/records",
    response_model=List[DecisionReplayRecord],
    status_code=status.HTTP_200_OK,
)
def list_replay_records() -> List[DecisionReplayRecord]:
    """Retrieves all persisted Decision Replay records from the in-memory audit ledger."""
    return replay_engine.list_records()


@app.post(
    "/api/v1/authority/commit",
    response_model=CommitResult,
    status_code=status.HTTP_200_OK,
)
def commit_plan(request: CommitRequest) -> CommitResult:
    """Executes OCC-checked manager approval commitment with transactional outbox generation."""
    snapshot = load_fixture_data()

    replan_report = recover_replan(
        RecoveryReplanRequest(
            rooftop_id=snapshot.rooftop.rooftop_id,
            snapshot_hash=snapshot.snapshot_hash or "",
        )
    )
    recommended = next((a for a in replan_report.alternatives if a.is_recommended), None)
    if not recommended:
        recommended = replan_report.alternatives[0] if replan_report.alternatives else None

    if not recommended:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recovery alternative available to commit.",
        )

    approval = ManagerRecoveryApproval(
        plan_id=recommended.plan_id,
        snapshot_hash=snapshot.snapshot_hash or "",
        approver_id=request.approver_id,
        approved_freight_usd=request.approved_freight_usd or Decimal("50.00"),
        valid_until=datetime.now(timezone.utc) + timedelta(hours=4),
    )
    commit_req = request.model_copy(update={"plan_id": recommended.plan_id})
    result = _authority_gateway.commit_recovery_plan(
        request=commit_req,
        current_snapshot=snapshot,
        candidate_alternative=recommended,
        approval=approval,
        evaluation_time_utc=REFERENCE_EVAL_TIME_UTC,
    )
    return result
