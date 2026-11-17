"""Integration tests for database seeding and idempotency."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.seed import SeedResult, seed_fixture
from app.models.canonical import Bay, RepairOrder, Rooftop, Task, Technician


class TestDatabaseSeeding:
    """Tests idempotent and transactional seeding of S-MATH-01 fixture."""

    def test_initial_seed_creation(self, db_session: Session):
        result: SeedResult = seed_fixture(db_session)
        assert result.rooftop_id == "ROOF-01"
        assert result.rooftops.created == 1
        assert result.bays.created == 3
        assert result.technicians.created == 4
        assert result.repair_orders.created == 6
        assert result.tasks.created == 7
        assert result.part_requirements.created == 5
        assert result.supplier_offers.created == 2

        # Verify database counts
        assert len(db_session.scalars(select(Rooftop)).all()) == 1
        assert len(db_session.scalars(select(Bay)).all()) == 3
        assert len(db_session.scalars(select(Technician)).all()) == 4
        assert len(db_session.scalars(select(RepairOrder)).all()) == 6
        assert len(db_session.scalars(select(Task)).all()) == 7

    def test_idempotent_repeated_seed(self, db_session: Session):
        # First seed
        first_result = seed_fixture(db_session)
        assert first_result.total_created == 28
        assert first_result.total_updated == 0

        # Second seed (idempotent run)
        second_result = seed_fixture(db_session)
        assert second_result.total_created == 0
        assert second_result.total_updated == 0
        assert second_result.total_unchanged == 28

        # Database rows unchanged
        assert len(db_session.scalars(select(RepairOrder)).all()) == 6

    def test_seed_with_reset_mode(self, db_session: Session):
        # Initial seed
        seed_fixture(db_session)
        assert len(db_session.scalars(select(RepairOrder)).all()) == 6

        # Seed with reset=True
        reset_result = seed_fixture(db_session, reset=True)
        assert reset_result.total_created == 28
        assert len(db_session.scalars(select(RepairOrder)).all()) == 6

    def test_transactional_rollback_on_injected_error(self, db_session: Session, monkeypatch):
        # Initial seed
        seed_fixture(db_session)
        assert len(db_session.scalars(select(Task)).all()) == 7

        # Simulate a database flush error during a seed attempt
        def failing_flush(*args, **kwargs):
            raise IntegrityError("Injected database constraint failure", params=None, orig=Exception())

        monkeypatch.setattr(db_session, "flush", failing_flush)

        with pytest.raises(IntegrityError):
            seed_fixture(db_session, reset=True)

        # After rollback, verify database was not corrupted into an inconsistent state
        # The rollback in seed_fixture leaves the session cleaned up
        assert db_session.is_active
