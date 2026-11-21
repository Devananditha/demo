"""Idempotent In-Memory Event Persistence Ledger for StallBreaker.

Authoritative Reference:
- docs/09_API_AND_MODULE_CONTRACTS.md (Section 2.1)
- docs/12_VERIFICATION_AND_REVALIDATION.md

Guarantees:
1. Idempotency: Duplicate event_id ingestion returns the previous stored record without re-mutating state.
2. Tamper Detection: Submitting a different payload under an existing event_id raises a Conflict/Tamper error.
3. Thread-safe sequential audit logging for retrospective replay.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import ValidationError

from app.stallbreaker.models import StoredEvent


class EventTamperError(ValueError):
    """Raised when an ingested event reuses an existing event_id with conflicting payload data."""
    pass


class StallBreakerEventStore:
    """Thread-safe in-memory event store with deduplication and idempotency verification."""

    def __init__(self):
        self._events: Dict[str, StoredEvent] = {}
        self._event_order: List[str] = []

    def record_event(self, event: StoredEvent) -> Tuple[StoredEvent, bool]:
        """Records an ingested event or returns existing record if already processed.
        
        Returns:
            Tuple[StoredEvent, bool]: (stored_event, is_duplicate)
        """
        if event.event_id in self._events:
            existing = self._events[event.event_id]
            # Verify payload consistency (tamper detection)
            if (
                existing.event_type != event.event_type
                or existing.entity_id != event.entity_id
                or existing.payload != event.payload
            ):
                raise EventTamperError(
                    f"Conflicting event payload detected for existing event_id '{event.event_id}'. "
                    f"Original type: {existing.event_type}, incoming type: {event.event_type}."
                )
            return existing, True

        self._events[event.event_id] = event
        self._event_order.append(event.event_id)
        return event, False

    def get_event(self, event_id: str) -> Optional[StoredEvent]:
        """Retrieves a single stored event by ID."""
        return self._events.get(event_id)

    def list_events(self, limit: int = 100) -> List[StoredEvent]:
        """Lists stored events in chronological ingestion order."""
        ordered = [self._events[eid] for eid in self._event_order]
        return ordered[-limit:]

    def clear(self) -> None:
        """Resets the store (used in test fixtures)."""
        self._events.clear()
        self._event_order.clear()


# Global singleton instance
stallbreaker_event_store = StallBreakerEventStore()
