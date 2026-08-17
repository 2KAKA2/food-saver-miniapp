"""Record the legal version accepted by each user.

Revision ID: 20260817_0003
Revises: 20260817_0002
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260817_0003"
down_revision: Union[str, None] = "20260817_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("legal_version", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("legal_accepted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "legal_accepted_at")
    op.drop_column("users", "legal_version")
