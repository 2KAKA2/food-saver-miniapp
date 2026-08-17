from datetime import date
from decimal import Decimal

from app.models.entities import InventoryBatch
from app.schemas.api import InventoryOut


STATUS_TEXT = {
    "normal": "正常",
    "expiring": "临期",
    "today": "今日到期",
    "expired": "已过期",
}


def calculate_status(expiry_date: date | None, today: date | None = None) -> tuple[str, int | None]:
    if expiry_date is None:
        return "normal", None
    days = (expiry_date - (today or date.today())).days
    if days < 0:
        return "expired", days
    if days == 0:
        return "today", days
    if days <= 3:
        return "expiring", days
    return "normal", days


def serialize_inventory(batch: InventoryBatch) -> InventoryOut:
    status, days = calculate_status(batch.expiry_date)
    return InventoryOut(
        id=batch.id,
        name=batch.name,
        category=batch.category,
        quantity=Decimal(batch.quantity),
        unit=batch.unit,
        location=batch.location,
        purchase_date=batch.purchase_date,
        expiry_date=batch.expiry_date,
        note=batch.note,
        status=status,
        status_text=STATUS_TEXT[status],
        days_remaining=days,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


def inventory_sort_key(batch: InventoryBatch):
    return (batch.expiry_date is None, batch.expiry_date or date.max, batch.name, batch.id)

