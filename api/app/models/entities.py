from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    openid: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    unionid: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    nickname: Mapped[str] = mapped_column(String(80), default="微信用户")
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Household(Base, TimestampMixin):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)


class HouseholdMember(Base):
    __tablename__ = "household_members"
    __table_args__ = (UniqueConstraint("household_id", "user_id", name="uq_household_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HouseholdInvite(Base):
    __tablename__ = "household_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class InventoryBatch(Base, TimestampMixin):
    __tablename__ = "inventory_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(40), default="其他")
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(20), default="份")
    location: Mapped[str] = mapped_column(String(30), default="冷藏")
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    note: Mapped[str] = mapped_column(String(255), default="")


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    servings: Mapped[int] = mapped_column(Integer, default=1)
    cook_time_minutes: Mapped[int] = mapped_column(Integer, default=20)
    difficulty: Mapped[str] = mapped_column(String(20), default="简单")
    ingredients_json: Mapped[str] = mapped_column(Text, default="[]")
    missing_ingredients_json: Mapped[str] = mapped_column(Text, default="[]")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str] = mapped_column(String(20), default="fallback")
    status: Mapped[str] = mapped_column(String(20), default="planned")
    cook_idempotency_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cook_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    cooked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class StockChange(Base):
    __tablename__ = "stock_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id"), nullable=True)
    batch_name: Mapped[str] = mapped_column(String(80))
    change_type: Mapped[str] = mapped_column(String(20))
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    before_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    after_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
