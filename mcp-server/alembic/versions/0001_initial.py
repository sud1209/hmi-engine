"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "house_listings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("zip_code", sa.String(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("beds", sa.Float(), nullable=False),
        sa.Column("baths", sa.Float(), nullable=False),
        sa.Column("sqft", sa.Integer(), nullable=False),
        sa.Column("property_type", sa.String(), nullable=False),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("lot_size", sa.Float(), nullable=True),
        sa.Column("posted_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "neighborhood_trends",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("zip_code", sa.String(), nullable=False),
        sa.Column("median_listing_price", sa.Integer(), nullable=False),
        sa.Column("median_days_on_market", sa.Integer(), nullable=False),
        sa.Column("inventory_count", sa.Integer(), nullable=False),
        sa.Column("school_score", sa.Float(), nullable=True),
        sa.Column("crime_score", sa.Float(), nullable=True),
        sa.Column("walk_score", sa.Float(), nullable=True),
        sa.Column("updated_date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "mortgage_rates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("term_years", sa.Integer(), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("updated_date", sa.Date(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "news_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("headline", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("relevance_score", sa.String(), nullable=True),
        sa.Column("market", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_table(
        "kpi_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("market", sa.String(), nullable=False),
        sa.Column("kpis", sa.JSON(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("kpi_snapshots")
    op.drop_table("news_items")
    op.drop_table("mortgage_rates")
    op.drop_table("neighborhood_trends")
    op.drop_table("house_listings")
