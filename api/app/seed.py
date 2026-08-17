import json
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import InventoryBatch, Recipe, StockChange


def seed_demo_data(db: Session):
    count = db.scalar(select(func.count()).select_from(InventoryBatch)) or 0
    if count:
        return
    today = date.today()
    batches = [
        InventoryBatch(name="西红柿", category="蔬菜", quantity=3, unit="个", location="冷藏", purchase_date=today, expiry_date=today + timedelta(days=1), note="优先食用"),
        InventoryBatch(name="鸡蛋", category="蛋奶", quantity=8, unit="个", location="冷藏", purchase_date=today, expiry_date=today + timedelta(days=7)),
        InventoryBatch(name="牛奶", category="蛋奶", quantity=1, unit="盒", location="冷藏", purchase_date=today, expiry_date=today + timedelta(days=2)),
        InventoryBatch(name="大米", category="主食", quantity=2, unit="kg", location="橱柜", purchase_date=today, expiry_date=today + timedelta(days=120)),
    ]
    db.add_all(batches)
    db.flush()
    for batch in batches:
        db.add(
            StockChange(
                batch_id=batch.id,
                batch_name=batch.name,
                change_type="add",
                quantity_change=Decimal(batch.quantity),
                before_quantity=Decimal("0"),
                after_quantity=Decimal(batch.quantity),
                reason="初始化演示数据",
            )
        )
    demo_recipe = Recipe(
        title="番茄炒蛋",
        servings=2,
        cook_time_minutes=15,
        difficulty="简单",
        ingredients_json=json.dumps(
            [
                {"inventory_id": batches[0].id, "name": "西红柿", "quantity": 2, "unit": "个", "available": True},
                {"inventory_id": batches[1].id, "name": "鸡蛋", "quantity": 3, "unit": "个", "available": True},
            ],
            ensure_ascii=False,
        ),
        missing_ingredients_json=json.dumps(
            [{"name": "盐", "quantity": 1, "unit": "小撮"}], ensure_ascii=False
        ),
        steps_json=json.dumps(
            ["西红柿切块，鸡蛋打散。", "鸡蛋炒熟后盛出。", "炒软西红柿，倒回鸡蛋调味。"],
            ensure_ascii=False,
        ),
        source="fallback",
    )
    db.add(demo_recipe)
    db.commit()

