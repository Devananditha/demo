"""Idempotent & Transactional Fixture Seeder for ServiceYield AI.

Guarantees:
1. Idempotency: Repeated execution leaves state unchanged and reports 0 creations.
2. Isolation: Operates strictly within the targeted rooftop_id without affecting other rooftops.
3. Transactional Integrity: All changes commit atomically; any failure triggers full rollback.
4. Detailed Accounting: Returns exact created, updated, and unchanged entity counts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.loader import load_fixture_data
from app.models.canonical import (
    Bay,
    PartRequirement,
    RepairOrder,
    Rooftop,
    SupplierOffer,
    Task,
    Technician,
)
from app.schemas.domain import DealershipSnapshotSchema


def _values_equal(val1: Any, val2: Any) -> bool:
    """Robust equality comparison handling datetimes and Decimals across SQLite/PostgreSQL."""
    if val1 is None or val2 is None:
        return val1 == val2
    if isinstance(val1, datetime) and isinstance(val2, datetime):
        # Normalize naive/aware datetimes to UTC for comparison
        d1 = val1 if val1.tzinfo is not None else val1.replace(tzinfo=timezone.utc)
        d2 = val2 if val2.tzinfo is not None else val2.replace(tzinfo=timezone.utc)
        return d1 == d2
    if isinstance(val1, Decimal) or isinstance(val2, Decimal):
        return Decimal(str(val1)) == Decimal(str(val2))
    return val1 == val2


@dataclass
class EntityCounts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


@dataclass
class SeedResult:
    rooftop_id: str
    snapshot_hash: str
    rooftops: EntityCounts = field(default_factory=EntityCounts)
    bays: EntityCounts = field(default_factory=EntityCounts)
    technicians: EntityCounts = field(default_factory=EntityCounts)
    repair_orders: EntityCounts = field(default_factory=EntityCounts)
    tasks: EntityCounts = field(default_factory=EntityCounts)
    part_requirements: EntityCounts = field(default_factory=EntityCounts)
    supplier_offers: EntityCounts = field(default_factory=EntityCounts)

    @property
    def total_created(self) -> int:
        return (
            self.rooftops.created
            + self.bays.created
            + self.technicians.created
            + self.repair_orders.created
            + self.tasks.created
            + self.part_requirements.created
            + self.supplier_offers.created
        )

    @property
    def total_updated(self) -> int:
        return (
            self.rooftops.updated
            + self.bays.updated
            + self.technicians.updated
            + self.repair_orders.updated
            + self.tasks.updated
            + self.part_requirements.updated
            + self.supplier_offers.updated
        )

    @property
    def total_unchanged(self) -> int:
        return (
            self.rooftops.unchanged
            + self.bays.unchanged
            + self.technicians.unchanged
            + self.repair_orders.unchanged
            + self.tasks.unchanged
            + self.part_requirements.unchanged
            + self.supplier_offers.unchanged
        )

    def summary(self) -> Dict[str, Any]:
        return {
            "rooftop_id": self.rooftop_id,
            "snapshot_hash": self.snapshot_hash,
            "total_created": self.total_created,
            "total_updated": self.total_updated,
            "total_unchanged": self.total_unchanged,
        }


def seed_fixture(
    session: Session,
    fixture_path: Optional[Path] = None,
    reset: bool = False,
) -> SeedResult:
    """Seeds canonical database with the S-MATH-01 synthetic fixture idempotently.
    
    Args:
        session: Active SQLAlchemy database session.
        fixture_path: Optional custom path to fixture JSON.
        reset: If True, purges and recreates all records belonging to this rooftop.
        
    Returns:
        SeedResult with full accounting of entity mutations.
    """
    snapshot: DealershipSnapshotSchema = load_fixture_data(fixture_path)
    rooftop_data = snapshot.rooftop
    rooftop_id = rooftop_data.rooftop_id
    result = SeedResult(rooftop_id=rooftop_id, snapshot_hash=snapshot.snapshot_hash or "")

    try:
        # If reset is requested, purge existing entities for this rooftop in dependency order
        if reset:
            existing_rooftop = session.get(Rooftop, rooftop_id)
            if existing_rooftop:
                session.delete(existing_rooftop)
                session.flush()

        # 1. Rooftop Upsert
        existing_rooftop = session.get(Rooftop, rooftop_id)
        if not existing_rooftop:
            rooftop_obj = Rooftop(
                rooftop_id=rooftop_data.rooftop_id,
                name=rooftop_data.name,
                timezone=rooftop_data.timezone,
                operating_day_start_tick=rooftop_data.operating_day_start_tick,
                operating_day_end_tick=rooftop_data.operating_day_end_tick,
                overtime_cutoff_tick=rooftop_data.overtime_cutoff_tick,
                version=rooftop_data.version,
                created_at=rooftop_data.created_at,
                updated_at=rooftop_data.updated_at,
            )
            session.add(rooftop_obj)
            result.rooftops.created += 1
        else:
            changed = False
            for attr in ["name", "timezone", "operating_day_start_tick", "operating_day_end_tick", "overtime_cutoff_tick", "version"]:
                if not _values_equal(getattr(existing_rooftop, attr), getattr(rooftop_data, attr)):
                    setattr(existing_rooftop, attr, getattr(rooftop_data, attr))
                    changed = True
            if changed:
                result.rooftops.updated += 1
            else:
                result.rooftops.unchanged += 1

        session.flush()

        # 2. Bays Upsert
        for bay_data in snapshot.bays:
            existing_bay = session.get(Bay, bay_data.bay_id)
            if not existing_bay:
                session.add(
                    Bay(
                        bay_id=bay_data.bay_id,
                        rooftop_id=bay_data.rooftop_id,
                        name=bay_data.name,
                        bay_type=bay_data.bay_type,
                        lifting_capacity_lbs=bay_data.lifting_capacity_lbs,
                        is_operational=bay_data.is_operational,
                        version=bay_data.version,
                    )
                )
                result.bays.created += 1
            else:
                changed = False
                for attr in ["name", "bay_type", "lifting_capacity_lbs", "is_operational", "version"]:
                    if not _values_equal(getattr(existing_bay, attr), getattr(bay_data, attr)):
                        setattr(existing_bay, attr, getattr(bay_data, attr))
                        changed = True
                if changed:
                    result.bays.updated += 1
                else:
                    result.bays.unchanged += 1

        session.flush()

        # 3. Technicians Upsert
        for tech_data in snapshot.technicians:
            existing_tech = session.get(Technician, tech_data.tech_id)
            if not existing_tech:
                session.add(
                    Technician(
                        tech_id=tech_data.tech_id,
                        rooftop_id=tech_data.rooftop_id,
                        display_name=tech_data.display_name,
                        skill_certifications=tech_data.skill_certifications,
                        shift_start_tick=tech_data.shift_start_tick,
                        shift_end_tick=tech_data.shift_end_tick,
                        lunch_start_tick=tech_data.lunch_start_tick,
                        lunch_duration_ticks=tech_data.lunch_duration_ticks,
                        is_active=tech_data.is_active,
                        version=tech_data.version,
                    )
                )
                result.technicians.created += 1
            else:
                changed = False
                for attr in [
                    "display_name",
                    "skill_certifications",
                    "shift_start_tick",
                    "shift_end_tick",
                    "lunch_start_tick",
                    "lunch_duration_ticks",
                    "is_active",
                    "version",
                ]:
                    if not _values_equal(getattr(existing_tech, attr), getattr(tech_data, attr)):
                        setattr(existing_tech, attr, getattr(tech_data, attr))
                        changed = True
                if changed:
                    result.technicians.updated += 1
                else:
                    result.technicians.unchanged += 1

        session.flush()

        # 4. Repair Orders Upsert
        for ro_data in snapshot.repair_orders:
            existing_ro = session.get(RepairOrder, ro_data.ro_id)
            if not existing_ro:
                session.add(
                    RepairOrder(
                        ro_id=ro_data.ro_id,
                        rooftop_id=ro_data.rooftop_id,
                        vehicle_id=ro_data.vehicle_id,
                        customer_id=ro_data.customer_id,
                        complaint=ro_data.complaint,
                        promised_at=ro_data.promised_at,
                        promise_tick=ro_data.promise_tick,
                        priority_weight=ro_data.priority_weight,
                        status=ro_data.status.value,
                        physical_state=ro_data.physical_state.value,
                        assigned_bay_id=ro_data.assigned_bay_id,
                        version=ro_data.version,
                        updated_at=ro_data.updated_at,
                    )
                )
                result.repair_orders.created += 1
            else:
                changed = False
                for attr in [
                    "vehicle_id",
                    "customer_id",
                    "complaint",
                    "promised_at",
                    "promise_tick",
                    "priority_weight",
                    "assigned_bay_id",
                    "version",
                ]:
                    if not _values_equal(getattr(existing_ro, attr), getattr(ro_data, attr)):
                        setattr(existing_ro, attr, getattr(ro_data, attr))
                        changed = True
                if existing_ro.status != ro_data.status.value:
                    existing_ro.status = ro_data.status.value
                    changed = True
                if existing_ro.physical_state != ro_data.physical_state.value:
                    existing_ro.physical_state = ro_data.physical_state.value
                    changed = True
                if changed:
                    result.repair_orders.updated += 1
                else:
                    result.repair_orders.unchanged += 1

        session.flush()

        # 5. Tasks Upsert
        for task_data in snapshot.tasks:
            existing_task = session.get(Task, task_data.task_id)
            if not existing_task:
                session.add(
                    Task(
                        task_id=task_data.task_id,
                        ro_id=task_data.ro_id,
                        sequence_order=task_data.sequence_order,
                        operation_code=task_data.operation_code,
                        description=task_data.description,
                        required_skill=task_data.required_skill,
                        required_bay_type=task_data.required_bay_type,
                        flat_rate_minutes=task_data.flat_rate_minutes,
                        estimated_duration_ticks=task_data.estimated_duration_ticks,
                        status=task_data.status.value,
                        predecessor_task_ids=task_data.predecessor_task_ids,
                        version=task_data.version,
                    )
                )
                result.tasks.created += 1
            else:
                changed = False
                for attr in [
                    "sequence_order",
                    "operation_code",
                    "description",
                    "required_skill",
                    "required_bay_type",
                    "flat_rate_minutes",
                    "estimated_duration_ticks",
                    "predecessor_task_ids",
                    "version",
                ]:
                    if not _values_equal(getattr(existing_task, attr), getattr(task_data, attr)):
                        setattr(existing_task, attr, getattr(task_data, attr))
                        changed = True
                if existing_task.status != task_data.status.value:
                    existing_task.status = task_data.status.value
                    changed = True
                if changed:
                    result.tasks.updated += 1
                else:
                    result.tasks.unchanged += 1

        session.flush()

        # 6. Part Requirements Upsert
        for part_data in snapshot.part_requirements:
            existing_part = session.get(PartRequirement, part_data.part_req_id)
            if not existing_part:
                session.add(
                    PartRequirement(
                        part_req_id=part_data.part_req_id,
                        ro_id=part_data.ro_id,
                        task_id=part_data.task_id,
                        oem_part_number=part_data.oem_part_number,
                        quantity=part_data.quantity,
                        vehicle_compatibility_ref=part_data.vehicle_compatibility_ref,
                        inventory_status=part_data.inventory_status.value,
                        usable_ready_tick=part_data.usable_ready_tick,
                        version=part_data.version,
                    )
                )
                result.part_requirements.created += 1
            else:
                changed = False
                for attr in [
                    "oem_part_number",
                    "quantity",
                    "vehicle_compatibility_ref",
                    "usable_ready_tick",
                    "version",
                ]:
                    if not _values_equal(getattr(existing_part, attr), getattr(part_data, attr)):
                        setattr(existing_part, attr, getattr(part_data, attr))
                        changed = True
                if existing_part.inventory_status != part_data.inventory_status.value:
                    existing_part.inventory_status = part_data.inventory_status.value
                    changed = True
                if changed:
                    result.part_requirements.updated += 1
                else:
                    result.part_requirements.unchanged += 1

        session.flush()

        # 7. Supplier Offers Upsert
        for offer_data in snapshot.supplier_offers:
            existing_offer = session.get(SupplierOffer, offer_data.offer_id)
            if not existing_offer:
                session.add(
                    SupplierOffer(
                        offer_id=offer_data.offer_id,
                        part_req_id=offer_data.part_req_id,
                        supplier_id=offer_data.supplier_id,
                        supplier_name=offer_data.supplier_name,
                        unit_cost_usd=offer_data.unit_cost_usd,
                        freight_surcharge_usd=offer_data.freight_surcharge_usd,
                        quoted_eta_tick=offer_data.quoted_eta_tick,
                        receiving_inspection_minutes=offer_data.receiving_inspection_minutes,
                        usable_ready_tick=offer_data.usable_ready_tick,
                        quote_valid_until=offer_data.quote_valid_until,
                        quote_status=offer_data.quote_status.value,
                        version=offer_data.version,
                    )
                )
                result.supplier_offers.created += 1
            else:
                changed = False
                for attr in [
                    "supplier_id",
                    "supplier_name",
                    "unit_cost_usd",
                    "freight_surcharge_usd",
                    "quoted_eta_tick",
                    "receiving_inspection_minutes",
                    "usable_ready_tick",
                    "quote_valid_until",
                    "version",
                ]:
                    if not _values_equal(getattr(existing_offer, attr), getattr(offer_data, attr)):
                        setattr(existing_offer, attr, getattr(offer_data, attr))
                        changed = True
                if existing_offer.quote_status != offer_data.quote_status.value:
                    existing_offer.quote_status = offer_data.quote_status.value
                    changed = True
                if changed:
                    result.supplier_offers.updated += 1
                else:
                    result.supplier_offers.unchanged += 1

        # Commit transaction atomically
        session.commit()
        return result

    except Exception:
        session.rollback()
        raise
