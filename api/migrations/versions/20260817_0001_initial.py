"""Initial production schema with users and household isolation.

Revision ID: 20260817_0001
Revises:
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260817_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("openid", sa.String(80), nullable=False),
        sa.Column("unionid", sa.String(80), nullable=True),
        sa.Column("nickname", sa.String(80), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("openid"),
    )
    op.create_index("ix_users_openid", "users", ["openid"], unique=True)
    op.create_index("ix_users_unionid", "users", ["unionid"])
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    op.create_table(
        "households",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_households_owner_id", "households", ["owner_id"])

    op.create_table(
        "household_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("household_id", "user_id", name="uq_household_member"),
    )
    op.create_index("ix_household_members_household_id", "household_members", ["household_id"])
    op.create_index("ix_household_members_user_id", "household_members", ["user_id"])

    op.create_table(
        "household_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("creator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_household_invites_household_id", "household_invites", ["household_id"])
    op.create_index("ix_household_invites_code_hash", "household_invites", ["code_hash"], unique=True)
    op.create_index("ix_household_invites_expires_at", "household_invites", ["expires_at"])

    op.create_table(
        "inventory_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("location", sa.String(30), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("note", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_inventory_batches_household_id", "inventory_batches", ["household_id"])
    op.create_index("ix_inventory_batches_created_by_user_id", "inventory_batches", ["created_by_user_id"])
    op.create_index("ix_inventory_batches_name", "inventory_batches", ["name"])
    op.create_index("ix_inventory_batches_expiry_date", "inventory_batches", ["expiry_date"])

    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=False),
        sa.Column("cook_time_minutes", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("ingredients_json", sa.Text(), nullable=False),
        sa.Column("missing_ingredients_json", sa.Text(), nullable=False),
        sa.Column("steps_json", sa.Text(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("cooked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_recipes_household_id", "recipes", ["household_id"])
    op.create_index("ix_recipes_created_by_user_id", "recipes", ["created_by_user_id"])

    op.create_table(
        "stock_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("inventory_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id"), nullable=True),
        sa.Column("batch_name", sa.String(80), nullable=False),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("quantity_change", sa.Numeric(12, 2), nullable=False),
        sa.Column("before_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("after_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_stock_changes_household_id", "stock_changes", ["household_id"])
    op.create_index("ix_stock_changes_actor_user_id", "stock_changes", ["actor_user_id"])
    op.create_index("ix_stock_changes_batch_id", "stock_changes", ["batch_id"])


def downgrade() -> None:
    op.drop_table("stock_changes")
    op.drop_table("recipes")
    op.drop_table("inventory_batches")
    op.drop_table("household_invites")
    op.drop_table("household_members")
    op.drop_table("households")
    op.drop_table("user_sessions")
    op.drop_table("users")

