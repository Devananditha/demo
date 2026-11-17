"""Pydantic v2 Canonical Domain Validation Schemas for ServiceYield AI.

Enforces:
- Strict enum typing for statuses, physical states, and skill codes.
- Positive constraints on durations, capacities, quantities, and monetary values.
- Valid tick ranges within horizon [0, 288].
- Cross-relational integrity on snapshots (referential integrity at validation time).
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============================================================================
# ENUM VOCABULARIES (Strict Canonical Set)
# ============================================================================

class ROStatus(str, Enum):
    """Documented Repair Order lifecycle statuses."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    STALLED = "STALLED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class VehiclePhysicalState(str, Enum):
    """Documented physical condition gates for vehicles."""
    IMMOBILIZED_ON_LIFT = "IMMOBILIZED_ON_LIFT"
    ROLLABLE = "ROLLABLE"
    IN_HOLDING = "IN_HOLDING"
    MOVE_PENDING = "MOVE_PENDING"
    UNKNOWN = "UNKNOWN"


class TaskStatus(str, Enum):
    """Internal task execution statuses."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    STALLED = "STALLED"


class PartInventoryStatus(str, Enum):
    """Part inventory and delivery states."""
    IN_STOCK = "IN_STOCK"
    IN_TRANSIT = "IN_TRANSIT"
    BACKORDERED = "BACKORDERED"
    UNKNOWN = "UNKNOWN"


class QuoteStatus(str, Enum):
    """Supplier offer validity states."""
    ACTIVE = "ACTIVE"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class SkillCode(str, Enum):
    """Standardized technician certification codes."""
    EV = "EV"
    DIAGNOSTIC = "DIAGNOSTIC"
    MECHANICAL = "MECHANICAL"
    TRANSMISSION = "TRANSMISSION"
    BRAKES = "BRAKES"
    SUSPENSION = "SUSPENSION"
    MAINTENANCE = "MAINTENANCE"
    FLUIDS = "FLUIDS"


class BayType(str, Enum):
    """Standardized service bay capability classes."""
    HEAVY_DIAGNOSTIC_LIFT = "HEAVY_DIAGNOSTIC_LIFT"
    STANDARD_2POST = "STANDARD_2POST"
    ALIGNMENT_RACK = "ALIGNMENT_RACK"
    EV_ISOLATION_BAY = "EV_ISOLATION_BAY"


# ============================================================================
# PYDANTIC DOMAIN ENTITY SCHEMAS
# ============================================================================

class CanonicalBaseModel(BaseModel):
    """Base model with common Pydantic v2 configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class RooftopSchema(CanonicalBaseModel):
    """Canonical dealership rooftop entity."""
    rooftop_id: str = Field(..., min_length=1, description="Unique rooftop identifier (e.g. ROOF-01)")
    name: str = Field(..., min_length=1, description="Dealership legal/display name")
    timezone: str = Field(default="UTC", description="IANA timezone (e.g. America/New_York, UTC)")
    operating_day_start_tick: int = Field(default=96, ge=0, le=288, description="Start tick of normal operations (08:00 = 96)")
    operating_day_end_tick: int = Field(default=204, ge=0, le=288, description="End tick of normal operations (17:00 = 204)")
    overtime_cutoff_tick: int = Field(default=228, ge=0, le=288, description="Latest allowable authorized overtime tick (19:00 = 228)")
    version: int = Field(default=1, ge=1, description="Entity mutation counter for OCC")
    created_at: datetime = Field(..., description="Creation timestamp with timezone")
    updated_at: datetime = Field(..., description="Last modification timestamp with timezone")

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Timestamps must be timezone-aware.")
        return v

    @model_validator(mode="after")
    def validate_operating_hours(self) -> "RooftopSchema":
        if self.operating_day_start_tick >= self.operating_day_end_tick:
            raise ValueError("operating_day_start_tick must be strictly less than operating_day_end_tick")
        if self.operating_day_end_tick > self.overtime_cutoff_tick:
            raise ValueError("operating_day_end_tick cannot exceed overtime_cutoff_tick")
        return self


class BaySchema(CanonicalBaseModel):
    """Physical service stall or equipment lift."""
    bay_id: str = Field(..., min_length=1, description="Unique bay identifier (e.g. BAY-01)")
    rooftop_id: str = Field(..., min_length=1, description="Associated rooftop identifier")
    name: str = Field(..., min_length=1, description="Display name for the bay")
    bay_type: str = Field(..., description="Bay capability category code")
    lifting_capacity_lbs: int = Field(..., gt=0, description="Rated lifting capacity in pounds")
    is_operational: bool = Field(default=True, description="Equipment operational status")
    version: int = Field(default=1, ge=1, description="Entity mutation counter for OCC")


class TechnicianSchema(CanonicalBaseModel):
    """Service technician available for work dispatch."""
    tech_id: str = Field(..., min_length=1, description="Unique technician identifier (e.g. TECH-01)")
    rooftop_id: str = Field(..., min_length=1, description="Associated rooftop identifier")
    display_name: str = Field(..., min_length=1, description="Technician name")
    skill_certifications: List[str] = Field(..., min_length=1, description="List of verified skill certification codes")
    shift_start_tick: int = Field(..., ge=0, le=288, description="Shift start in discrete ticks")
    shift_end_tick: int = Field(..., ge=0, le=288, description="Shift end in discrete ticks")
    lunch_start_tick: int = Field(..., ge=0, le=288, description="Mandatory meal break start in ticks")
    lunch_duration_ticks: int = Field(default=12, gt=0, le=24, description="Mandatory meal break duration in ticks (default 12 = 60m)")
    is_active: bool = Field(default=True, description="Active employment and shift status")
    version: int = Field(default=1, ge=1, description="Entity mutation counter for OCC")

    @model_validator(mode="after")
    def validate_shift_and_lunch(self) -> "TechnicianSchema":
        if self.shift_start_tick >= self.shift_end_tick:
            raise ValueError(f"Technician shift start ({self.shift_start_tick}) must precede shift end ({self.shift_end_tick})")
        lunch_end = self.lunch_start_tick + self.lunch_duration_ticks
        if not (self.shift_start_tick <= self.lunch_start_tick and lunch_end <= self.shift_end_tick):
            raise ValueError(
                f"Lunch window [{self.lunch_start_tick}, {lunch_end}] must fall entirely within shift [{self.shift_start_tick}, {self.shift_end_tick}]"
            )
        return self


class RepairOrderSchema(CanonicalBaseModel):
    """Customer or internal vehicle repair contract."""
    ro_id: str = Field(..., min_length=1, description="Unique RO identifier (e.g. RO-104)")
    rooftop_id: str = Field(..., min_length=1, description="Associated rooftop identifier")
    vehicle_id: str = Field(..., min_length=1, description="Synthetic vehicle asset identifier")
    customer_id: str = Field(..., min_length=1, description="Synthetic customer identifier")
    complaint: str = Field(..., min_length=1, description="Primary customer complaint / stated concern")
    promised_at: datetime = Field(..., description="Customer promised completion datetime (timezone-aware)")
    promise_tick: int = Field(..., ge=0, le=288, description="Promised completion time in discrete ticks")
    priority_weight: int = Field(default=1, ge=1, le=10, description="Customer/service priority scalar (w_r)")
    status: ROStatus = Field(..., description="Lifecycle status")
    physical_state: VehiclePhysicalState = Field(..., description="Current physical vehicle condition")
    assigned_bay_id: Optional[str] = Field(default=None, description="Currently occupied bay if stalled/in-progress")
    version: int = Field(default=1, ge=1, description="Entity mutation counter for OCC")
    updated_at: datetime = Field(..., description="Last modification timestamp with timezone")

    @field_validator("promised_at", "updated_at")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Timestamps must be timezone-aware.")
        return v


class TaskSchema(CanonicalBaseModel):
    """Discrete mechanical or diagnostic operation within a repair order."""
    task_id: str = Field(..., min_length=1, description="Unique task identifier (e.g. TASK-104-01)")
    ro_id: str = Field(..., min_length=1, description="Associated Repair Order ID")
    sequence_order: int = Field(..., ge=1, description="Topological execution order index")
    operation_code: str = Field(..., min_length=1, description="DMS labor operation code (e.g. TRANS-SOL-REP)")
    description: str = Field(..., min_length=1, description="Human-readable task description")
    required_skill: str = Field(..., min_length=1, description="Required skill certification code")
    required_bay_type: str = Field(..., min_length=1, description="Required bay capability class")
    flat_rate_minutes: int = Field(..., gt=0, description="OEM/DMS flat-rate labor minutes")
    estimated_duration_ticks: int = Field(..., gt=0, le=288, description="Estimated work duration in discrete 5-min ticks")
    status: TaskStatus = Field(..., description="Task execution status")
    predecessor_task_ids: List[str] = Field(default_factory=list, description="IDs of tasks that must complete before this task starts")
    version: int = Field(default=1, ge=1, description="Entity mutation counter for OCC")


class PartRequirementSchema(CanonicalBaseModel):
    """Bill-of-materials component required to complete a task."""
    part_req_id: str = Field(..., min_length=1, description="Unique requirement identifier")
    ro_id: str = Field(..., min_length=1, description="Associated Repair Order ID")
    task_id: str = Field(..., min_length=1, description="Task requiring this part")
    oem_part_number: str = Field(..., min_length=1, description="Manufacturer part number")
    quantity: int = Field(default=1, ge=1, description="Quantity required")
    vehicle_compatibility_ref: Optional[str] = Field(default=None, description="ACES/fitment compatibility reference")
    inventory_status: PartInventoryStatus = Field(..., description="Current stock or shipment state")
    usable_ready_tick: Optional[int] = Field(default=None, ge=0, le=288, description="Tick when part is inspected and physically ready for assembly")
    version: int = Field(default=1, ge=1, description="Entity mutation counter for OCC")


class SupplierOfferSchema(CanonicalBaseModel):
    """Candidate sourcing offer for a required replacement part."""
    offer_id: str = Field(..., min_length=1, description="Unique offer identifier (e.g. OFFER-104-S1)")
    part_req_id: str = Field(..., min_length=1, description="Associated part requirement ID")
    supplier_id: str = Field(..., min_length=1, description="Supplier code (e.g. S1_HOTSHOT, S2_SISTER_STORE)")
    supplier_name: str = Field(..., min_length=1, description="Supplier display name")
    unit_cost_usd: Decimal = Field(..., ge=Decimal("0.00"), description="Base unit wholesale purchase price")
    freight_surcharge_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Expedited courier freight surcharge")
    quoted_eta_tick: int = Field(..., ge=0, le=288, description="Quoted arrival time in discrete ticks")
    receiving_inspection_minutes: int = Field(default=15, ge=0, description="Mandatory dealership intake inspection time in minutes")
    usable_ready_tick: int = Field(..., ge=0, le=288, description="Tick when part is ready for technician pickup")
    quote_valid_until: datetime = Field(..., description="Available-To-Promise (ATP) quote expiration timestamp")
    quote_status: QuoteStatus = Field(default=QuoteStatus.ACTIVE, description="Quote validity state")
    version: int = Field(default=1, ge=1, description="Entity mutation counter for OCC")

    @field_validator("quote_valid_until")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("quote_valid_until must be timezone-aware.")
        return v

    @model_validator(mode="after")
    def validate_inspection_delay(self) -> "SupplierOfferSchema":
        if self.usable_ready_tick < self.quoted_eta_tick:
            raise ValueError(f"usable_ready_tick ({self.usable_ready_tick}) cannot be earlier than quoted_eta_tick ({self.quoted_eta_tick})")
        return self


# ============================================================================
# CANONICAL DEALERSHIP SNAPSHOT SCHEMA
# ============================================================================

class DealershipSnapshotSchema(CanonicalBaseModel):
    """Full relational snapshot of a dealership's fixed operations state."""
    rooftop: RooftopSchema
    bays: List[BaySchema] = Field(..., min_length=1)
    technicians: List[TechnicianSchema] = Field(..., min_length=1)
    repair_orders: List[RepairOrderSchema] = Field(..., min_length=1)
    tasks: List[TaskSchema] = Field(..., min_length=1)
    part_requirements: List[PartRequirementSchema] = Field(default_factory=list)
    supplier_offers: List[SupplierOfferSchema] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    snapshot_hash: Optional[str] = Field(default=None, description="SHA-256 state snapshot integrity hash")

    @model_validator(mode="after")
    def validate_relational_integrity(self) -> "DealershipSnapshotSchema":
        """Enforces referential integrity across the snapshot entities."""
        rooftop_id = self.rooftop.rooftop_id
        bay_ids = {b.bay_id for b in self.bays}
        ro_ids = {r.ro_id for r in self.repair_orders}
        task_ids = {t.task_id for t in self.tasks}
        part_req_ids = {p.part_req_id for p in self.part_requirements}

        # Check unique identifiers within collections
        if len(bay_ids) != len(self.bays):
            raise ValueError("Duplicate bay_id found in bays collection")
        if len({t.tech_id for t in self.technicians}) != len(self.technicians):
            raise ValueError("Duplicate tech_id found in technicians collection")
        if len(ro_ids) != len(self.repair_orders):
            raise ValueError("Duplicate ro_id found in repair_orders collection")
        if len(task_ids) != len(self.tasks):
            raise ValueError("Duplicate task_id found in tasks collection")
        if len(part_req_ids) != len(self.part_requirements):
            raise ValueError("Duplicate part_req_id found in part_requirements collection")
        if len({s.offer_id for s in self.supplier_offers}) != len(self.supplier_offers):
            raise ValueError("Duplicate offer_id found in supplier_offers collection")

        # Check foreign keys to rooftop
        for b in self.bays:
            if b.rooftop_id != rooftop_id:
                raise ValueError(f"Bay {b.bay_id} references rooftop {b.rooftop_id}, expected {rooftop_id}")
        for t in self.technicians:
            if t.rooftop_id != rooftop_id:
                raise ValueError(f"Technician {t.tech_id} references rooftop {t.rooftop_id}, expected {rooftop_id}")
        for r in self.repair_orders:
            if r.rooftop_id != rooftop_id:
                raise ValueError(f"RepairOrder {r.ro_id} references rooftop {r.rooftop_id}, expected {rooftop_id}")
            if r.assigned_bay_id and r.assigned_bay_id not in bay_ids:
                raise ValueError(f"RepairOrder {r.ro_id} assigned_bay_id {r.assigned_bay_id} does not exist in bays")

        # Check task foreign keys
        for task in self.tasks:
            if task.ro_id not in ro_ids:
                raise ValueError(f"Task {task.task_id} references non-existent ro_id {task.ro_id}")
            for pred_id in task.predecessor_task_ids:
                if pred_id not in task_ids:
                    raise ValueError(f"Task {task.task_id} references non-existent predecessor {pred_id}")

        # Check part requirement foreign keys
        for part in self.part_requirements:
            if part.ro_id not in ro_ids:
                raise ValueError(f"PartRequirement {part.part_req_id} references non-existent ro_id {part.ro_id}")
            if part.task_id not in task_ids:
                raise ValueError(f"PartRequirement {part.part_req_id} references non-existent task_id {part.task_id}")

        # Check supplier offer foreign keys
        for offer in self.supplier_offers:
            if offer.part_req_id not in part_req_ids:
                raise ValueError(f"SupplierOffer {offer.offer_id} references non-existent part_req_id {offer.part_req_id}")

        return self
