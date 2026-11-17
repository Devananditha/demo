"""Initial canonical domain schema for ServiceYield AI.

Revision ID: 001_initial_canonical_schema
Revises: 
Create Date: 2026-11-18 08:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_canonical_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. rooftops
    op.create_table(
        "rooftops",
        sa.Column("rooftop_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("operating_day_start_tick", sa.Integer(), nullable=False, server_default="96"),
        sa.Column("operating_day_end_tick", sa.Integer(), nullable=False, server_default="204"),
        sa.Column("overtime_cutoff_tick", sa.Integer(), nullable=False, server_default="228"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("operating_day_start_tick < operating_day_end_tick", name="check_rooftop_operating_hours"),
        sa.CheckConstraint("version >= 1", name="check_rooftop_version_positive"),
    )

    # 2. bays
    op.create_table(
        "bays",
        sa.Column("bay_id", sa.String(length=64), primary_key=True),
        sa.Column("rooftop_id", sa.String(length=64), sa.ForeignKey("rooftops.rooftop_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("bay_type", sa.String(length=64), nullable=False),
        sa.Column("lifting_capacity_lbs", sa.Integer(), nullable=False),
        sa.Column("is_operational", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("lifting_capacity_lbs > 0", name="check_positive_bay_capacity"),
        sa.CheckConstraint("version >= 1", name="check_bay_version_positive"),
    )

    # 3. technicians
    op.create_table(
        "technicians",
        sa.Column("tech_id", sa.String(length=64), primary_key=True),
        sa.Column("rooftop_id", sa.String(length=64), sa.ForeignKey("rooftops.rooftop_id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("skill_certifications", sa.JSON(), nullable=False),
        sa.Column("shift_start_tick", sa.Integer(), nullable=False),
        sa.Column("shift_end_tick", sa.Integer(), nullable=False),
        sa.Column("lunch_start_tick", sa.Integer(), nullable=False),
        sa.Column("lunch_duration_ticks", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("shift_start_tick < shift_end_tick", name="check_technician_shift_bounds"),
        sa.CheckConstraint("lunch_duration_ticks > 0", name="check_technician_lunch_duration"),
        sa.CheckConstraint("version >= 1", name="check_technician_version_positive"),
    )

    # 4. repair_orders
    op.create_table(
        "repair_orders",
        sa.Column("ro_id", sa.String(length=64), primary_key=True),
        sa.Column("rooftop_id", sa.String(length=64), sa.ForeignKey("rooftops.rooftop_id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=64), nullable=False),
        sa.Column("complaint", sa.Text(), nullable=False),
        sa.Column("promised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("promise_tick", sa.Integer(), nullable=False),
        sa.Column("priority_weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("physical_state", sa.String(length=32), nullable=False),
        sa.Column("assigned_bay_id", sa.String(length=64), sa.ForeignKey("bays.bay_id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('OPEN', 'IN_PROGRESS', 'STALLED', 'COMPLETED', 'CLOSED')", name="check_ro_valid_status"),
        sa.CheckConstraint("physical_state IN ('IMMOBILIZED_ON_LIFT', 'ROLLABLE', 'IN_HOLDING', 'MOVE_PENDING', 'UNKNOWN')", name="check_ro_valid_physical_state"),
        sa.CheckConstraint("priority_weight >= 1", name="check_ro_positive_priority"),
        sa.CheckConstraint("version >= 1", name="check_ro_version_positive"),
    )

    # 5. tasks
    op.create_table(
        "tasks",
        sa.Column("task_id", sa.String(length=64), primary_key=True),
        sa.Column("ro_id", sa.String(length=64), sa.ForeignKey("repair_orders.ro_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("operation_code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skill", sa.String(length=64), nullable=False),
        sa.Column("required_bay_type", sa.String(length=64), nullable=False),
        sa.Column("flat_rate_minutes", sa.Integer(), nullable=False),
        sa.Column("estimated_duration_ticks", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("predecessor_task_ids", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("sequence_order >= 1", name="check_task_sequence_order"),
        sa.CheckConstraint("flat_rate_minutes > 0", name="check_task_positive_flat_rate"),
        sa.CheckConstraint("estimated_duration_ticks > 0", name="check_task_positive_duration"),
        sa.CheckConstraint("status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'STALLED')", name="check_task_valid_status"),
        sa.CheckConstraint("version >= 1", name="check_task_version_positive"),
    )

    # 6. part_requirements
    op.create_table(
        "part_requirements",
        sa.Column("part_req_id", sa.String(length=64), primary_key=True),
        sa.Column("ro_id", sa.String(length=64), sa.ForeignKey("repair_orders.ro_id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(length=64), sa.ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False),
        sa.Column("oem_part_number", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("vehicle_compatibility_ref", sa.String(length=128), nullable=True),
        sa.Column("inventory_status", sa.String(length=32), nullable=False),
        sa.Column("usable_ready_tick", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("quantity >= 1", name="check_positive_part_quantity"),
        sa.CheckConstraint("inventory_status IN ('IN_STOCK', 'IN_TRANSIT', 'BACKORDERED', 'UNKNOWN')", name="check_valid_part_inventory_status"),
        sa.CheckConstraint("version >= 1", name="check_part_req_version_positive"),
    )

    # 7. supplier_offers
    op.create_table(
        "supplier_offers",
        sa.Column("offer_id", sa.String(length=64), primary_key=True),
        sa.Column("part_req_id", sa.String(length=64), sa.ForeignKey("part_requirements.part_req_id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("unit_cost_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("freight_surcharge_usd", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("quoted_eta_tick", sa.Integer(), nullable=False),
        sa.Column("receiving_inspection_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("usable_ready_tick", sa.Integer(), nullable=False),
        sa.Column("quote_valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quote_status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("unit_cost_usd >= 0", name="check_positive_unit_cost"),
        sa.CheckConstraint("freight_surcharge_usd >= 0", name="check_positive_freight"),
        sa.CheckConstraint("quote_status IN ('ACTIVE', 'ACCEPTED', 'EXPIRED', 'REJECTED')", name="check_valid_quote_status"),
        sa.CheckConstraint("usable_ready_tick >= quoted_eta_tick", name="check_usable_after_quoted_eta"),
        sa.CheckConstraint("version >= 1", name="check_supplier_offer_version_positive"),
    )


def downgrade() -> None:
    op.drop_table("supplier_offers")
    op.drop_table("part_requirements")
    op.drop_table("tasks")
    op.drop_table("repair_orders")
    op.drop_table("technicians")
    op.drop_table("bays")
    op.drop_table("rooftops")
