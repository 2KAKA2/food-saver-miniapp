from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import InventoryBatch, StockChange
from app.schemas.api import InventoryInput, InventoryOut
from app.services.auth import HouseholdContext, get_household_context
from app.services.inventory import calculate_status, inventory_sort_key, serialize_inventory


router = APIRouter()


@router.get("", response_model=list[InventoryOut])
def list_inventory(
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str = "",
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    if status_filter not in {None, "normal", "expiring", "today", "expired"}:
        raise HTTPException(status_code=422, detail="不支持的库存状态")
    query = select(InventoryBatch).where(
        InventoryBatch.household_id == context.household.id,
        InventoryBatch.quantity > 0,
    )
    if keyword.strip():
        query = query.where(InventoryBatch.name.contains(keyword.strip()))
    batches = sorted(db.scalars(query).all(), key=inventory_sort_key)
    if status_filter:
        batches = [item for item in batches if calculate_status(item.expiry_date)[0] == status_filter]
    return [serialize_inventory(item) for item in batches]


@router.post("", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
def create_inventory(
    payload: InventoryInput,
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    batch = InventoryBatch(
        household_id=context.household.id,
        created_by_user_id=context.user.id,
        **payload.model_dump(),
    )
    db.add(batch)
    db.flush()
    db.add(
        StockChange(
            household_id=context.household.id,
            actor_user_id=context.user.id,
            batch_id=batch.id,
            batch_name=batch.name,
            change_type="add",
            quantity_change=payload.quantity,
            before_quantity=Decimal("0"),
            after_quantity=payload.quantity,
            reason="新增库存",
        )
    )
    db.commit()
    db.refresh(batch)
    return serialize_inventory(batch)


@router.put("/{batch_id}", response_model=InventoryOut)
def update_inventory(
    batch_id: int,
    payload: InventoryInput,
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    batch = db.get(InventoryBatch, batch_id)
    if not batch or batch.household_id != context.household.id:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    before = Decimal(batch.quantity)
    for field, value in payload.model_dump().items():
        setattr(batch, field, value)
    db.flush()
    db.add(
        StockChange(
            household_id=context.household.id,
            actor_user_id=context.user.id,
            batch_id=batch.id,
            batch_name=batch.name,
            change_type="update",
            quantity_change=payload.quantity - before,
            before_quantity=before,
            after_quantity=payload.quantity,
            reason="编辑库存",
        )
    )
    db.commit()
    db.refresh(batch)
    return serialize_inventory(batch)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(
    batch_id: int,
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    batch = db.get(InventoryBatch, batch_id)
    if not batch or batch.household_id != context.household.id:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    before = Decimal(batch.quantity)
    db.add(
        StockChange(
            household_id=context.household.id,
            actor_user_id=context.user.id,
            batch_id=None,
            batch_name=batch.name,
            change_type="delete",
            quantity_change=-before,
            before_quantity=before,
            after_quantity=Decimal("0"),
            reason="删除库存",
        )
    )
    db.delete(batch)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
