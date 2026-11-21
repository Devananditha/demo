"""Deterministic State Mutator for Dealership Domain Events.

Authoritative Reference:
- docs/07_CANONICAL_STATE_AND_DOMAIN_MODEL.md
- docs/08_SHARED_CONSTRAINTS_C1_C7.md
- docs/09_API_AND_MODULE_CONTRACTS.md
"""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional, Tuple

from app.core.snapshot import compute_snapshot_hash_from_dict
from app.schemas.domain import (
    BaySchema,
    DealershipSnapshotSchema,
    PartInventoryStatus,
    PartRequirementSchema,
    RepairOrderSchema,
    ROStatus,
    TaskSchema,
    TaskStatus,
    TechnicianSchema,
    VehiclePhysicalState,
)
from app.stallbreaker.models import EventIngestRequest, EventType


class DealershipStateMutator:
    """Applies domain event state transitions to a canonical DealershipSnapshotSchema."""

    @staticmethod
    def apply_event(
        snapshot: DealershipSnapshotSchema,
        event: EventIngestRequest,
    ) -> Tuple[DealershipSnapshotSchema, bool, Optional[str]]:
        """Applies validated event transition, increments OCC versions, and recomputes SHA-256 hash.
        
        Returns:
            Tuple[DealershipSnapshotSchema, bool, Optional[str]]:
                (mutated_snapshot, requires_recovery, disruption_summary)
        """
        # Check OCC expected snapshot hash
        if event.expected_snapshot_hash and event.expected_snapshot_hash != snapshot.snapshot_hash:
            raise ValueError(
                f"Stale state OCC conflict: expected '{event.expected_snapshot_hash}', actual '{snapshot.snapshot_hash}'"
            )

        # Validate known event type
        if event.event_type not in (
            EventType.PARTS_ETA_CHANGED,
            EventType.PART_UNAVAILABLE,
            EventType.TECHNICIAN_UNAVAILABLE,
            EventType.BAY_RESERVATION_CHANGED,
            EventType.OPERATION_COMPLETED,
            EventType.RO_LINE_READY,
            EventType.RO_OPENED,
        ):
            raise ValueError(f"Unknown or unsupported event type: '{event.event_type}'")

        # Create a deep copy to preserve immutability of the input snapshot
        mutated = snapshot.model_copy(deep=True)
        requires_recovery = False
        disruption_summary: Optional[str] = None

        if event.event_type == EventType.PARTS_ETA_CHANGED:
            target_part_id = event.entity_id or event.payload.get("part_req_id")
            new_ready_tick = event.payload.get("new_ready_tick") or event.payload.get("new_eta_tick", 198)
            delay_minutes = event.payload.get("delay_minutes", 180)

            found = False
            for part in mutated.part_requirements:
                if part.part_req_id == target_part_id:
                    part.usable_ready_tick = new_ready_tick
                    part.inventory_status = PartInventoryStatus.IN_TRANSIT
                    part.version += 1
                    found = True
                    break

            if not found:
                raise ValueError(f"Target part_req_id '{target_part_id}' not found in snapshot.")

            requires_recovery = True
            disruption_summary = (
                f"Part '{target_part_id}' delivery slipped {delay_minutes} min to tick {new_ready_tick}. "
                f"Disrupts dependent reassembly task."
            )

        elif event.event_type == EventType.PART_UNAVAILABLE:
            target_part_id = event.entity_id or event.payload.get("part_req_id")
            reason = event.payload.get("reason", "SUPPLIER_BACKORDERED")

            found = False
            for part in mutated.part_requirements:
                if part.part_req_id == target_part_id:
                    part.inventory_status = PartInventoryStatus.BACKORDERED
                    part.usable_ready_tick = None
                    part.version += 1
                    found = True
                    break

            if not found:
                raise ValueError(f"Target part_req_id '{target_part_id}' not found in snapshot.")

            requires_recovery = True
            disruption_summary = f"Part '{target_part_id}' is unavailable ({reason}). Active schedule blocked under C2."

        elif event.event_type == EventType.TECHNICIAN_UNAVAILABLE:
            target_tech_id = event.entity_id or event.payload.get("tech_id")
            reason = event.payload.get("reason", "UNSCHEDULED_ABSENCE")

            found = False
            for tech in mutated.technicians:
                if tech.tech_id == target_tech_id:
                    tech.is_active = False
                    tech.version += 1
                    found = True
                    break

            if not found:
                raise ValueError(f"Target tech_id '{target_tech_id}' not found in snapshot.")

            requires_recovery = True
            disruption_summary = f"Technician '{target_tech_id}' unavailable ({reason}). Active task assignments invalidated under C6."

        elif event.event_type == EventType.BAY_RESERVATION_CHANGED:
            target_bay_id = event.entity_id or event.payload.get("bay_id")
            is_operational = event.payload.get("is_operational", False)
            reason = event.payload.get("reason", "EQUIPMENT_MAINTENANCE")

            found = False
            for bay in mutated.bays:
                if bay.bay_id == target_bay_id:
                    bay.is_operational = is_operational
                    bay.version += 1
                    found = True
                    break

            if not found:
                raise ValueError(f"Target bay_id '{target_bay_id}' not found in snapshot.")

            requires_recovery = not is_operational
            disruption_summary = (
                f"Bay '{target_bay_id}' operational status changed to {is_operational} ({reason})."
                if not is_operational else f"Bay '{target_bay_id}' operational status restored."
            )

        elif event.event_type == EventType.OPERATION_COMPLETED:
            target_task_id = event.entity_id or event.payload.get("task_id")
            found = False
            for task in mutated.tasks:
                if task.task_id == target_task_id:
                    task.status = TaskStatus.COMPLETED
                    task.version += 1
                    found = True
                    break

            if not found:
                raise ValueError(f"Target task_id '{target_task_id}' not found in snapshot.")

            disruption_summary = f"Operation '{target_task_id}' successfully marked COMPLETED."

        elif event.event_type == EventType.RO_LINE_READY:
            target_ro_id = event.entity_id or event.payload.get("ro_id")
            found = False
            for ro in mutated.repair_orders:
                if ro.ro_id == target_ro_id:
                    if ro.status == ROStatus.STALLED:
                        ro.status = ROStatus.IN_PROGRESS
                    ro.version += 1
                    found = True
                    break

            if not found:
                raise ValueError(f"Target ro_id '{target_ro_id}' not found in snapshot.")

            disruption_summary = f"RO line '{target_ro_id}' readiness updated to READY."

        elif event.event_type == EventType.RO_OPENED:
            # Simple metadata update or increment
            target_ro_id = event.entity_id or event.payload.get("ro_id", "RO-NEW")
            disruption_summary = f"New RO '{target_ro_id}' opened."

        # Increment rooftop version to signify snapshot mutation
        mutated.rooftop.version += 1
        mutated.rooftop.updated_at = datetime.now(timezone.utc)

        # Compute deterministic new SHA-256 snapshot hash
        new_hash = compute_snapshot_hash_from_dict(mutated.model_dump(mode="json"))
        mutated.snapshot_hash = new_hash

        return mutated, requires_recovery, disruption_summary
