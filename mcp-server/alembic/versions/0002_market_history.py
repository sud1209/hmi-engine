"""Add market_history_snapshots table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_history_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("market", sa.String(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("median_dom", sa.Integer(), nullable=True),
        sa.Column("months_supply", sa.Float(), nullable=True),
        sa.Column("mortgage_rate_30yr", sa.Float(), nullable=True),
        sa.Column("price_per_sqft", sa.Integer(), nullable=True),
        sa.Column("active_listings", sa.Integer(), nullable=True),
        sa.Column("median_sale_price", sa.Integer(), nullable=True),
        sa.Column("sales_volume", sa.Integer(), nullable=True),
        sa.Column("new_listings", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_history_market", "market_history_snapshots", ["market"])
    op.create_index("ix_market_history_month", "market_history_snapshots", ["month"])


def downgrade() -> None:
    op.drop_index("ix_market_history_month", table_name="market_history_snapshots")
    op.drop_index("ix_market_history_market", table_name="market_history_snapshots")
    op.drop_table("market_history_snapshots")
