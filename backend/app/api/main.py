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
from app.schemas.domain import DealershipSnapshotSchema, EconomicParametersSchema
from app.verifier.models import CandidateSchedulePlan, VerificationResult
from app.verifier.sweep_oracle import SweepLineOracle
from app.stallbreaker import (
    DealershipStateMutator,
    EventIngestRequest,
    EventIngestResponse,
    EventType,
    StallBreakerApprovalRequest,
    StallBreakerDisruptionAnalysis,
    StallBreakerRecoveryReport,
    StoredEvent,
    is_production_mode,
    stallbreaker_approval_gateway,
    stallbreaker_engine,
    stallbreaker_event_store,
    validate_event_timestamp,
    verify_hmac_sha256,
)

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
    disrupted_ro_id: Optional[str] = Field(default=None, description="Anchor disrupted repair order")
    disrupted_part_req_id: Optional[str] = Field(default=None, description="Affected part requirement")
    trigger_tick: Optional[int] = Field(default=159, ge=0, le=288, description="Evaluation/disruption tick")
    primary_supplier_delay_minutes: Optional[int] = Field(default=180, ge=0, description="Reported supplier delay in minutes")
    allow_emergency_overtime: bool = Field(default=True, description="Authorize overtime to complete reassembly")
    economic_parameters: Optional[EconomicParametersSchema] = Field(default=None, description="Configured economic parameters")


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rooftop_id: str = Field(..., min_length=1, description="Target dealership rooftop identifier")
    snapshot_hash: str = Field(..., min_length=1, description="Expected snapshot SHA-256 hash")
    plan: CandidateSchedulePlan = Field(..., description="Candidate schedule plan to independently audit")


class DisruptionAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(..., min_length=1, description="Target event ID to analyze")
    plan: Optional[CandidateSchedulePlan] = Field(default=None, description="Optional active schedule plan to audit")


class RecoveryRecommendationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: Optional[str] = Field(default=None, description="Triggering event identifier")
    rooftop_id: Optional[str] = Field(default=None, description="Optional rooftop identifier")
    allow_emergency_overtime: bool = Field(default=True, description="Authorize emergency overtime for recovery")


# Authority commit gateway singleton
_authority_gateway = AuthorityCommitGateway()

# Module-level live snapshot mutable state
_live_snapshot: DealershipSnapshotSchema = load_fixture_data()

def get_live_snapshot() -> DealershipSnapshotSchema:
    global _live_snapshot
    return _live_snapshot

def reset_live_snapshot() -> DealershipSnapshotSchema:
    global _live_snapshot
    _live_snapshot = load_fixture_data()
    return _live_snapshot


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/api/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def get_health() -> HealthResponse:
    """Service health probe endpoint."""
    return HealthResponse(status="ok")


@app.get("/api/v1/state", response_model=DealershipStateResponse, status_code=status.HTTP_200_OK)
def get_canonical_state() -> DealershipStateResponse:
    """Loads and returns canonical workshop state from S-MATH-01 fixture or live mutated state."""
    snapshot = get_live_snapshot()

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
    snapshot = get_live_snapshot()

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
    snapshot = get_live_snapshot()

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
    snapshot = get_live_snapshot()

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
    snapshot = get_live_snapshot()

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

    target_ro_id = request.disrupted_ro_id
    if not target_ro_id:
        stalled_ro = next((ro for ro in snapshot.repair_orders if ro.status.value in ("STALLED", "BLOCKED")), None)
        target_ro_id = stalled_ro.ro_id if stalled_ro else (snapshot.repair_orders[0].ro_id if snapshot.repair_orders else "RO-104")

    target_part_id = request.disrupted_part_req_id
    if not target_part_id:
        part = next((p for p in snapshot.part_requirements if p.ro_id == target_ro_id), None)
        target_part_id = part.part_req_id if part else (snapshot.part_requirements[0].part_req_id if snapshot.part_requirements else "PART-REQ-104-SOLENOID")

    target_part = next((p for p in snapshot.part_requirements if p.part_req_id == target_part_id), None)
    delayed_tick = 198
    if target_part and target_part.usable_ready_tick:
        delayed_tick = target_part.usable_ready_tick

    delay_mins = request.primary_supplier_delay_minutes if request.primary_supplier_delay_minutes is not None else 180

    disruption = DisruptionEvent(
        disrupted_ro_id=target_ro_id,
        disrupted_part_req_id=target_part_id,
        disruption_type=DisruptionType.PARTS_DELAY,
        trigger_tick=request.trigger_tick or REFERENCE_CURRENT_TICK,
        primary_supplier_delay_minutes=delay_mins,
        delayed_ready_tick=delayed_tick,
        description=f"Supplier primary ground transit delayed {delay_mins} min to tick {delayed_tick}",
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
    snapshot = get_live_snapshot()

    if request.rooftop_id != snapshot.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    cand_snap = snapshot
    plan_id = request.plan.plan_id
    if plan_id.startswith("PLAN-REC-"):
        option_id = plan_id[len("PLAN-REC-"):]
        matched_offer = next((o for o in snapshot.supplier_offers if o.offer_id == option_id), None)
        if matched_offer:
            cand_snap = snapshot.model_copy(deep=True)
            for p in cand_snap.part_requirements:
                if p.part_req_id == matched_offer.part_req_id:
                    p.usable_ready_tick = (
                        matched_offer.usable_ready_tick
                        if matched_offer.usable_ready_tick is not None
                        else (matched_offer.quoted_eta_tick + (matched_offer.receiving_inspection_minutes // 5))
                    )

    oracle = SweepLineOracle(cand_snap)
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
    snapshot = get_live_snapshot()

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


# ============================================================================
# STALLBREAKER EVENT-DRIVEN DISRUPTION & RECOVERY ENDPOINTS
# ============================================================================

@app.post(
    "/api/v1/stallbreaker/events",
    response_model=EventIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_stallbreaker_event(request: EventIngestRequest) -> EventIngestResponse:
    """Ingests, validates, and applies domain events with HMAC verification and idempotency."""
    global _live_snapshot

    if request.rooftop_id != _live_snapshot.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    # 1. Cryptographic HMAC-SHA256 signature verification & timestamp freshness
    if is_production_mode() and not request.signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HMAC-SHA256 signature required in production mode.",
        )

    if request.signature:
        if not verify_hmac_sha256(request.payload, request.signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid HMAC-SHA256 event signature.",
            )

    if request.occurred_at:
        if not validate_event_timestamp(request.occurred_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stale or future event timestamp: exceeds allowable clock skew window.",
            )

    # 2. Check Idempotency via Event Store
    existing_event = stallbreaker_event_store.get_event(request.event_id)
    if existing_event:
        return EventIngestResponse(
            status="DUPLICATE_IGNORED",
            event_id=existing_event.event_id,
            is_duplicate=True,
            previous_snapshot_hash=existing_event.snapshot_hash_before,
            new_snapshot_hash=existing_event.snapshot_hash_after,
            requires_recovery=False,
            disruption_summary="Event already ingested. State mutation bypassed (idempotent).",
        )

    # 3. OCC Expected Hash Check (if specified)
    if request.expected_snapshot_hash and request.expected_snapshot_hash != _live_snapshot.snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"OCC conflict: expected '{request.expected_snapshot_hash}', actual '{_live_snapshot.snapshot_hash}'.",
        )

    hash_before = _live_snapshot.snapshot_hash or ""

    # 4. Apply State Transition
    try:
        mutated_snap, requires_recovery, disruption_summary = DealershipStateMutator.apply_event(
            _live_snapshot, request
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"State transition error: {str(exc)}",
        )

    hash_after = mutated_snap.snapshot_hash or ""
    _live_snapshot = mutated_snap

    # 5. Record Event in Persistence Store
    now = datetime.now(timezone.utc)
    stored = StoredEvent(
        event_id=request.event_id,
        rooftop_id=request.rooftop_id,
        event_type=request.event_type,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        payload=request.payload,
        occurred_at=request.occurred_at or now,
        ingested_at=now,
        signature=request.signature,
        snapshot_hash_before=hash_before,
        snapshot_hash_after=hash_after,
    )
    stallbreaker_event_store.record_event(stored)

    return EventIngestResponse(
        status="ACCEPTED",
        event_id=request.event_id,
        is_duplicate=False,
        previous_snapshot_hash=hash_before,
        new_snapshot_hash=hash_after,
        requires_recovery=requires_recovery,
        disruption_summary=disruption_summary,
        ingested_at=now,
    )


@app.get(
    "/api/v1/stallbreaker/events",
    response_model=List[StoredEvent],
    status_code=status.HTTP_200_OK,
)
def list_stallbreaker_events() -> List[StoredEvent]:
    """Retrieves all persisted events from the append-only StallBreaker audit ledger."""
    return stallbreaker_event_store.list_events()


@app.get(
    "/api/v1/stallbreaker/state",
    response_model=DealershipStateResponse,
    status_code=status.HTTP_200_OK,
)
def get_stallbreaker_live_state() -> DealershipStateResponse:
    """Returns the current active (mutated) dealership operational state."""
    snap = get_live_snapshot()
    ro_items = [
        RepairOrderStateItem(
            ro_id=ro.ro_id,
            status=ro.status.value if hasattr(ro.status, "value") else str(ro.status),
            physical_state=ro.physical_state.value if hasattr(ro.physical_state, "value") else str(ro.physical_state),
            assigned_bay_id=ro.assigned_bay_id,
            promise_tick=ro.promise_tick,
        )
        for ro in snap.repair_orders
    ]
    return DealershipStateResponse(
        rooftop_id=snap.rooftop.rooftop_id,
        snapshot_hash=snap.snapshot_hash or "",
        evaluation_tick=REFERENCE_CURRENT_TICK,
        operating_day_end_tick=snap.rooftop.operating_day_end_tick,
        overtime_cutoff_tick=snap.rooftop.overtime_cutoff_tick,
        repair_orders=ro_items,
    )


@app.post(
    "/api/v1/stallbreaker/disruption-analysis",
    response_model=StallBreakerDisruptionAnalysis,
    status_code=status.HTTP_200_OK,
)
def analyze_stallbreaker_disruption(request: DisruptionAnalysisRequest) -> StallBreakerDisruptionAnalysis:
    """Evaluates the consequences of an event on shop capacity and active schedules."""
    if not request.event_id or not request.event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disruption analysis request requires a non-empty 'event_id'.",
        )

    snap = get_live_snapshot()

    event = stallbreaker_event_store.get_event(request.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disruption event '{request.event_id}' not found in event store.",
        )

    if event.rooftop_id != snap.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disruption event '{request.event_id}' belongs to rooftop '{event.rooftop_id}', not active rooftop '{snap.rooftop.rooftop_id}'.",
        )

    analysis = stallbreaker_engine.analyze_disruption(snap, event, current_schedule=request.plan)
    return analysis


@app.post(
    "/api/v1/stallbreaker/recovery-recommendations",
    response_model=StallBreakerRecoveryReport,
    status_code=status.HTTP_200_OK,
)
def get_recovery_recommendations(request: RecoveryRecommendationsRequest) -> StallBreakerRecoveryReport:
    """Generates feasible recovery actions, executes CP-SAT re-solve, and computes Decision Replay."""
    if not request.event_id or not request.event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active event-driven recovery request must contain a non-empty 'event_id'.",
        )

    snap = get_live_snapshot()

    if request.rooftop_id and request.rooftop_id != snap.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    event = stallbreaker_event_store.get_event(request.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disruption event '{request.event_id}' not found in event store.",
        )

    if event.rooftop_id != snap.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disruption event '{request.event_id}' belongs to rooftop '{event.rooftop_id}', not active rooftop '{snap.rooftop.rooftop_id}'.",
        )

    report = stallbreaker_engine.generate_recovery_recommendations(
        snapshot=snap,
        event=event,
        allow_emergency_overtime=request.allow_emergency_overtime,
        evaluation_time_utc=REFERENCE_EVAL_TIME_UTC,
    )
    return report


@app.get(
    "/api/v1/stallbreaker/replay/{replay_id}",
    response_model=DecisionReplayRecord,
    status_code=status.HTTP_200_OK,
)
def get_stallbreaker_replay_record(replay_id: str) -> DecisionReplayRecord:
    """Retrieves a specific Decision Replay record by its identifier."""
    record = replay_engine.get_record(replay_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision Replay record '{replay_id}' not found.",
        )
    return record


@app.post(
    "/api/v1/stallbreaker/approve",
    response_model=CommitResult,
    status_code=status.HTTP_200_OK,
)
def approve_stallbreaker_recovery(request: StallBreakerApprovalRequest) -> CommitResult:
    """Version-bound manager approval with OCC fresh-state revalidation and outbox dispatch."""
    if not request.event_id or not request.event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval request requires a non-empty 'event_id'.",
        )

    if not request.plan_id or not request.plan_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval request requires a non-empty 'plan_id'.",
        )

    snap = get_live_snapshot()

    event = stallbreaker_event_store.get_event(request.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disruption event '{request.event_id}' not found in event store.",
        )

    if event.rooftop_id != snap.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disruption event '{request.event_id}' belongs to rooftop '{event.rooftop_id}', not active rooftop '{snap.rooftop.rooftop_id}'.",
        )

    # Recompute recovery alternatives using the exact event and current snapshot
    report = stallbreaker_engine.generate_recovery_recommendations(
        snapshot=snap,
        event=event,
        allow_emergency_overtime=True,
        evaluation_time_utc=REFERENCE_EVAL_TIME_UTC,
    )

    candidate = next((a for a in report.evaluated_alternatives if a.plan_id == request.plan_id), None)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recovery plan '{request.plan_id}' not found among active recovery candidates for event '{request.event_id}'.",
        )

    result = stallbreaker_approval_gateway.process_approval(
        request=request,
        current_snapshot=snap,
        candidate_alternative=candidate,
        evaluation_time_utc=REFERENCE_EVAL_TIME_UTC,
    )
    return result


from app.benchmark.models import BenchmarkSuiteReport, ScenarioBenchmarkResult
from app.benchmark.runner import benchmark_runner

# Global cached benchmark report
_cached_benchmark_report: Optional[BenchmarkSuiteReport] = None


@app.get(
    "/api/v1/benchmark/results",
    response_model=BenchmarkSuiteReport,
    status_code=status.HTTP_200_OK,
)
def get_benchmark_results(seed: int = 42) -> BenchmarkSuiteReport:
    """Returns the comprehensive benchmark evaluation report across all 7 synthetic scenarios."""
    global _cached_benchmark_report
    if _cached_benchmark_report is None or _cached_benchmark_report.scenarios[0].seed != seed:
        _cached_benchmark_report = benchmark_runner.run_full_suite(seed=seed)
    return _cached_benchmark_report


@app.post(
    "/api/v1/benchmark/run",
    response_model=BenchmarkSuiteReport,
    status_code=status.HTTP_200_OK,
)
def run_benchmark_suite(seed: int = 42) -> BenchmarkSuiteReport:
    """Triggers an on-demand benchmark execution across all 7 scenarios and 4 dispatch methods."""
    global _cached_benchmark_report
    _cached_benchmark_report = benchmark_runner.run_full_suite(seed=seed)
    return _cached_benchmark_report

