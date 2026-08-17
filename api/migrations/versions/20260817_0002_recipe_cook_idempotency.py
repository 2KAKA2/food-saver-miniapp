"""Add idempotent recipe cooking result.

Revision ID: 20260817_0002
Revises: 20260817_0001
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260817_0002"
down_revision: Union[str, None] = "20260817_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("cook_idempotency_key_hash", sa.String(64), nullable=True))
    op.add_column("recipes", sa.Column("cook_result_json", sa.Text(), nullable=True))
    op.create_index(
        "ix_recipes_cook_idempotency_key_hash",
        "recipes",
        ["cook_idempotency_key_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_recipes_cook_idempotency_key_hash", table_name="recipes")
    op.drop_column("recipes", "cook_result_json")
    op.drop_column("recipes", "cook_idempotency_key_hash")

