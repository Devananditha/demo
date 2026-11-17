"""SQLAlchemy 2.0 Canonical Relational Domain Models for ServiceYield AI.

Implements:
- Rooftop (Dealership site)
- Bay (Physical service lifting capacity)
- Technician (Service technician shift & skills)
- RepairOrder (Customer repair contract)
- Task (Mechanical/diagnostic DAG operation)
- PartRequirement (Bill of materials requirement)
- SupplierOffer (Candidate sourcing quote)
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Rooftop(Base):
    """Canonical dealership rooftop entity."""
    __tablename__ = "rooftops"

    rooftop_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    operating_day_start_tick: Mapped[int] = mapped_column(Integer, nullable=False, default=96)
    operating_day_end_tick: Mapped[int] = mapped_column(Integer, nullable=False, default=204)
    overtime_cutoff_tick: Mapped[int] = mapped_column(Integer, nullable=False, default=228)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )

    # Relationships
    bays: Mapped[List["Bay"]] = relationship(back_populates="rooftop", cascade="all, delete-orphan")
    technicians: Mapped[List["Technician"]] = relationship(back_populates="rooftop", cascade="all, delete-orphan")
    repair_orders: Mapped[List["RepairOrder"]] = relationship(back_populates="rooftop", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "operating_day_start_tick < operating_day_end_tick",
            name="check_rooftop_operating_hours"
        ),
        CheckConstraint(
            "version >= 1",
            name="check_rooftop_version_positive"
        ),
    )


class Bay(Base):
    """Physical service stall or equipment lift in the workshop."""
    __tablename__ = "bays"

    bay_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rooftop_id: Mapped[str] = mapped_column(String(64), ForeignKey("rooftops.rooftop_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bay_type: Mapped[str] = mapped_column(String(64), nullable=False)
    lifting_capacity_lbs: Mapped[int] = mapped_column(Integer, nullable=False)
    is_operational: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    rooftop: Mapped["Rooftop"] = relationship(back_populates="bays")
    assigned_repair_orders: Mapped[List["RepairOrder"]] = relationship(back_populates="assigned_bay")

    __table_args__ = (
        CheckConstraint("lifting_capacity_lbs > 0", name="check_positive_bay_capacity"),
        CheckConstraint("version >= 1", name="check_bay_version_positive"),
    )


class Technician(Base):
    """Service technician available for work dispatch."""
    __tablename__ = "technicians"

    tech_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rooftop_id: Mapped[str] = mapped_column(String(64), ForeignKey("rooftops.rooftop_id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_certifications: Mapped[list] = mapped_column(JSON, nullable=False)
    shift_start_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    shift_end_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    lunch_start_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    lunch_duration_ticks: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    rooftop: Mapped["Rooftop"] = relationship(back_populates="technicians")

    __table_args__ = (
        CheckConstraint("shift_start_tick < shift_end_tick", name="check_technician_shift_bounds"),
        CheckConstraint("lunch_duration_ticks > 0", name="check_technician_lunch_duration"),
        CheckConstraint("version >= 1", name="check_technician_version_positive"),
    )


class RepairOrder(Base):
    """Customer or internal vehicle repair contract."""
    __tablename__ = "repair_orders"

    ro_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rooftop_id: Mapped[str] = mapped_column(String(64), ForeignKey("rooftops.rooftop_id", ondelete="CASCADE"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    complaint: Mapped[str] = mapped_column(Text, nullable=False)
    promised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    promise_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    physical_state: Mapped[str] = mapped_column(String(32), nullable=False)
    assigned_bay_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("bays.bay_id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )

    # Relationships
    rooftop: Mapped["Rooftop"] = relationship(back_populates="repair_orders")
    assigned_bay: Mapped[Optional["Bay"]] = relationship(back_populates="assigned_repair_orders")
    tasks: Mapped[List["Task"]] = relationship(back_populates="repair_order", cascade="all, delete-orphan")
    part_requirements: Mapped[List["PartRequirement"]] = relationship(
        back_populates="repair_order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'STALLED', 'COMPLETED', 'CLOSED')",
            name="check_ro_valid_status"
        ),
        CheckConstraint(
            "physical_state IN ('IMMOBILIZED_ON_LIFT', 'ROLLABLE', 'IN_HOLDING', 'MOVE_PENDING', 'UNKNOWN')",
            name="check_ro_valid_physical_state"
        ),
        CheckConstraint("priority_weight >= 1", name="check_ro_positive_priority"),
        CheckConstraint("version >= 1", name="check_ro_version_positive"),
    )


class Task(Base):
    """Discrete mechanical or diagnostic operation within a repair order."""
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ro_id: Mapped[str] = mapped_column(String(64), ForeignKey("repair_orders.ro_id", ondelete="CASCADE"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skill: Mapped[str] = mapped_column(String(64), nullable=False)
    required_bay_type: Mapped[str] = mapped_column(String(64), nullable=False)
    flat_rate_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_duration_ticks: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    predecessor_task_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    repair_order: Mapped["RepairOrder"] = relationship(back_populates="tasks")
    part_requirements: Mapped[List["PartRequirement"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("sequence_order >= 1", name="check_task_sequence_order"),
        CheckConstraint("flat_rate_minutes > 0", name="check_task_positive_flat_rate"),
        CheckConstraint("estimated_duration_ticks > 0", name="check_task_positive_duration"),
        CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'STALLED')",
            name="check_task_valid_status"
        ),
        CheckConstraint("version >= 1", name="check_task_version_positive"),
    )


class PartRequirement(Base):
    """Bill-of-materials component required to complete a task."""
    __tablename__ = "part_requirements"

    part_req_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ro_id: Mapped[str] = mapped_column(String(64), ForeignKey("repair_orders.ro_id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)
    oem_part_number: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    vehicle_compatibility_ref: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    inventory_status: Mapped[str] = mapped_column(String(32), nullable=False)
    usable_ready_tick: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    repair_order: Mapped["RepairOrder"] = relationship(back_populates="part_requirements")
    task: Mapped["Task"] = relationship(back_populates="part_requirements")
    supplier_offers: Mapped[List["SupplierOffer"]] = relationship(
        back_populates="part_requirement", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="check_positive_part_quantity"),
        CheckConstraint(
            "inventory_status IN ('IN_STOCK', 'IN_TRANSIT', 'BACKORDERED', 'UNKNOWN')",
            name="check_valid_part_inventory_status"
        ),
        CheckConstraint("version >= 1", name="check_part_req_version_positive"),
    )


class SupplierOffer(Base):
    """Candidate sourcing offer for a required replacement part."""
    __tablename__ = "supplier_offers"

    offer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    part_req_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("part_requirements.part_req_id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    freight_surcharge_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    quoted_eta_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    receiving_inspection_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    usable_ready_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    quote_valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quote_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    part_requirement: Mapped["PartRequirement"] = relationship(back_populates="supplier_offers")

    __table_args__ = (
        CheckConstraint("unit_cost_usd >= 0", name="check_positive_unit_cost"),
        CheckConstraint("freight_surcharge_usd >= 0", name="check_positive_freight"),
        CheckConstraint(
            "quote_status IN ('ACTIVE', 'ACCEPTED', 'EXPIRED', 'REJECTED')",
            name="check_valid_quote_status"
        ),
        CheckConstraint("usable_ready_tick >= quoted_eta_tick", name="check_usable_after_quoted_eta"),
        CheckConstraint("version >= 1", name="check_supplier_offer_version_positive"),
    )
