from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import InventoryBatch
from app.schemas.api import DashboardOut
from app.services.inventory import calculate_status, inventory_sort_key, serialize_inventory


router = APIRouter()


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    batches = db.scalars(
        select(InventoryBatch).where(InventoryBatch.user_id == 1, InventoryBatch.quantity > 0)
    ).all()
    counters = {"normal": 0, "expiring": 0, "today": 0, "expired": 0}
    urgent = []
    for batch in batches:
        status, _ = calculate_status(batch.expiry_date)
        counters[status] += 1
        if status in {"expiring", "today", "expired"}:
            urgent.append(batch)
    urgent = sorted(urgent, key=inventory_sort_key)[:8]
    return DashboardOut(
        inventory_count=len(batches),
        normal_count=counters["normal"],
        expiring_count=counters["expiring"],
        today_count=counters["today"],
        expired_count=counters["expired"],
        expiring_items=[serialize_inventory(item) for item in urgent],
    )

