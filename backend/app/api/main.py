"""Read-Only FastAPI Application for ServiceYield AI Decision Replay Telemetry.

Authoritative Reference:
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.2: Calculate Readiness)
- PROJECT_RULES.md
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.data.loader import load_fixture_data
from app.predict.classifier import PredictReadinessClassifier
from app.predict.models import DealershipReadinessReport

# Reference Evaluation Timestamp for S-MATH-01 Fixture
REFERENCE_EVAL_TIME_UTC = datetime(2026, 11, 18, 13, 15, 0, tzinfo=timezone.utc)
REFERENCE_CURRENT_TICK = 159

app = FastAPI(
    title="ServiceYield AI — Read-Only Predict Readiness API",
    version="0.1.0",
    description="Advisory decision-intelligence telemetry service exposing canonical state and Predict Layer 1 readiness.",
)

# CORS configuration restricted strictly to local frontend dev server
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


@app.get("/api/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def get_health() -> HealthResponse:
    """Service health probe endpoint."""
    return HealthResponse(status="ok")


@app.get("/api/v1/state", response_model=DealershipStateResponse, status_code=status.HTTP_200_OK)
def get_canonical_state() -> DealershipStateResponse:
    """Loads and returns canonical workshop state from S-MATH-01 fixture.
    
    Does not invent technician assignments or unrecorded fixture evidence.
    """
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
    """Calculates Layer 1 Empirical-Bayes readiness classifications for all active ROs.
    
    Validates rooftop identity and rejects stale snapshot hashes with HTTP 409.
    Executes actual deterministic PredictReadinessClassifier logic.
    """
    snapshot = load_fixture_data()

    # Validate rooftop existence
    if request.rooftop_id != snapshot.rooftop.rooftop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rooftop '{request.rooftop_id}' not found.",
        )

    # Validate snapshot concurrency token (optimistic concurrency control)
    if request.snapshot_hash != snapshot.snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stale snapshot hash: expected '{snapshot.snapshot_hash}', received '{request.snapshot_hash}'.",
        )

    # Evaluate using actual deterministic classifier logic
    classifier = PredictReadinessClassifier()
    report = classifier.assess_dealership_readiness(
        snapshot,
        current_tick=REFERENCE_CURRENT_TICK,
        now_utc=REFERENCE_EVAL_TIME_UTC,
    )

    return report
