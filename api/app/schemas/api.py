from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InventoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="其他", max_length=40)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit: str = Field(default="份", min_length=1, max_length=20)
    location: str = Field(default="冷藏", max_length=30)
    purchase_date: date | None = None
    expiry_date: date | None = None
    note: str = Field(default="", max_length=255)

    @field_validator("name", "category", "unit", "location", "note", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("expiry_date")
    @classmethod
    def expiry_not_before_purchase(cls, value, info):
        purchase_date = info.data.get("purchase_date")
        if value and purchase_date and value < purchase_date:
            raise ValueError("到期日期不能早于购买日期")
        return value


class InventoryOut(InventoryInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Literal["normal", "expiring", "today", "expired"]
    status_text: str
    days_remaining: int | None
    created_at: datetime
    updated_at: datetime


class DashboardOut(BaseModel):
    inventory_count: int
    normal_count: int
    expiring_count: int
    today_count: int
    expired_count: int
    expiring_items: list[InventoryOut]


class RecognizedIngredient(BaseModel):
    name: str
    category: str = "其他"
    quantity: Decimal = Decimal("1")
    unit: str = "份"
    confidence: float = Field(default=0.5, ge=0, le=1)


class RecognitionOut(BaseModel):
    source: Literal["ai", "fallback"]
    items: list[RecognizedIngredient]
    message: str = ""


class RecipeGenerateRequest(BaseModel):
    inventory_ids: list[int] = Field(default_factory=list)
    servings: int = Field(default=2, ge=1, le=10)
    flavor: str = Field(default="家常", max_length=30)
    max_minutes: int = Field(default=30, ge=5, le=240)


class RecipeIngredient(BaseModel):
    inventory_id: int | None = None
    name: str
    quantity: Decimal = Field(gt=0)
    unit: str
    available: bool = True


class MissingIngredient(BaseModel):
    name: str
    quantity: Decimal = Field(gt=0)
    unit: str


class RecipeOut(BaseModel):
    id: int
    title: str
    servings: int
    cook_time_minutes: int
    difficulty: str
    ingredients: list[RecipeIngredient]
    missing_ingredients: list[MissingIngredient]
    steps: list[str]
    source: Literal["ai", "fallback"]
    status: Literal["planned", "cooked"]
    created_at: datetime
    cooked_at: datetime | None = None


class ConsumptionItem(BaseModel):
    inventory_id: int
    quantity: Decimal = Field(gt=0)


class CookRequest(BaseModel):
    consumptions: list[ConsumptionItem] = Field(min_length=1)


class CookOut(BaseModel):
    recipe: RecipeOut
    updated_inventory: list[InventoryOut]

