import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import InventoryBatch, Recipe, StockChange
from app.schemas.api import (
    CookOut,
    CookRequest,
    MissingIngredient,
    RecipeGenerateRequest,
    RecipeIngredient,
    RecipeOut,
)
from app.services.ai import generate_recipe
from app.services.inventory import calculate_status, inventory_sort_key, serialize_inventory


router = APIRouter()


def serialize_recipe(recipe: Recipe) -> RecipeOut:
    return RecipeOut(
        id=recipe.id,
        title=recipe.title,
        servings=recipe.servings,
        cook_time_minutes=recipe.cook_time_minutes,
        difficulty=recipe.difficulty,
        ingredients=[RecipeIngredient.model_validate(item) for item in json.loads(recipe.ingredients_json)],
        missing_ingredients=[
            MissingIngredient.model_validate(item) for item in json.loads(recipe.missing_ingredients_json)
        ],
        steps=json.loads(recipe.steps_json),
        source=recipe.source,
        status=recipe.status,
        created_at=recipe.created_at,
        cooked_at=recipe.cooked_at,
    )


def _normalize_result(result: dict, valid_batches: dict[int, InventoryBatch], payload: RecipeGenerateRequest):
    ingredients = []
    for raw in result.get("ingredients", []):
        try:
            item = RecipeIngredient.model_validate(raw)
        except ValidationError:
            continue
        if item.inventory_id is not None:
            batch = valid_batches.get(item.inventory_id)
            if not batch:
                item.inventory_id = None
                item.available = False
            elif item.quantity > Decimal(batch.quantity):
                item.quantity = Decimal(batch.quantity)
        ingredients.append(item)
    missing = []
    for raw in result.get("missing_ingredients", []):
        try:
            missing.append(MissingIngredient.model_validate(raw))
        except ValidationError:
            continue
    steps = [str(step).strip() for step in result.get("steps", []) if str(step).strip()]
    if not steps:
        steps = ["清洗并处理食材。", "依次烹饪至熟透。", "调味后装盘。"]
    return {
        "title": str(result.get("title") or "AI 推荐菜谱")[:120],
        "servings": payload.servings,
        "cook_time_minutes": max(5, min(int(result.get("cook_time_minutes", 20)), payload.max_minutes)),
        "difficulty": str(result.get("difficulty") or "简单")[:20],
        "ingredients": [item.model_dump(mode="json") for item in ingredients],
        "missing_ingredients": [item.model_dump(mode="json") for item in missing],
        "steps": steps,
        "source": "ai" if result.get("source") == "ai" else "fallback",
    }


@router.post("/generate", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(payload: RecipeGenerateRequest, db: Session = Depends(get_db)):
    query = select(InventoryBatch).where(InventoryBatch.user_id == 1, InventoryBatch.quantity > 0)
    if payload.inventory_ids:
        query = query.where(InventoryBatch.id.in_(payload.inventory_ids))
    batches = [
        item
        for item in db.scalars(query).all()
        if calculate_status(item.expiry_date)[0] != "expired"
    ]
    batches.sort(
        key=lambda item: (
            {"today": 0, "expiring": 1, "normal": 2}.get(calculate_status(item.expiry_date)[0], 3),
            inventory_sort_key(item),
        )
    )
    if not batches:
        raise HTTPException(status_code=400, detail="没有可用于生成菜谱的库存食材")
    raw_result = generate_recipe(batches, payload.servings, payload.flavor, payload.max_minutes)
    result = _normalize_result(raw_result, {item.id: item for item in batches}, payload)
    recipe = Recipe(
        user_id=1,
        title=result["title"],
        servings=result["servings"],
        cook_time_minutes=result["cook_time_minutes"],
        difficulty=result["difficulty"],
        ingredients_json=json.dumps(result["ingredients"], ensure_ascii=False),
        missing_ingredients_json=json.dumps(result["missing_ingredients"], ensure_ascii=False),
        steps_json=json.dumps(result["steps"], ensure_ascii=False),
        source=result["source"],
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return serialize_recipe(recipe)


@router.get("", response_model=list[RecipeOut])
def list_recipes(db: Session = Depends(get_db)):
    recipes = db.scalars(
        select(Recipe).where(Recipe.user_id == 1).order_by(Recipe.created_at.desc(), Recipe.id.desc())
    ).all()
    return [serialize_recipe(item) for item in recipes]


@router.get("/{recipe_id}", response_model=RecipeOut)
def recipe_detail(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe or recipe.user_id != 1:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return serialize_recipe(recipe)


@router.post("/{recipe_id}/cook", response_model=CookOut)
def cook_recipe(recipe_id: int, payload: CookRequest, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe or recipe.user_id != 1:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    if recipe.status == "cooked":
        raise HTTPException(status_code=409, detail="该菜谱已经确认制作")

    merged: dict[int, Decimal] = {}
    for item in payload.consumptions:
        merged[item.inventory_id] = merged.get(item.inventory_id, Decimal("0")) + item.quantity

    batches = {
        item.id: item
        for item in db.scalars(
            select(InventoryBatch).where(
                InventoryBatch.user_id == 1,
                InventoryBatch.id.in_(merged.keys()),
            )
        ).all()
    }
    for batch_id, quantity in merged.items():
        batch = batches.get(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"库存记录 {batch_id} 不存在")
        if Decimal(batch.quantity) < quantity:
            raise HTTPException(status_code=409, detail=f"{batch.name}库存不足")

    updated = []
    for batch_id, quantity in merged.items():
        batch = batches[batch_id]
        before = Decimal(batch.quantity)
        batch.quantity = before - quantity
        db.add(
            StockChange(
                user_id=1,
                batch_id=batch.id,
                recipe_id=recipe.id,
                batch_name=batch.name,
                change_type="cook",
                quantity_change=-quantity,
                before_quantity=before,
                after_quantity=batch.quantity,
                reason=f"制作菜谱：{recipe.title}",
            )
        )
        updated.append(batch)
    recipe.status = "cooked"
    recipe.cooked_at = datetime.now()
    db.commit()
    for batch in updated:
        db.refresh(batch)
    db.refresh(recipe)
    return CookOut(
        recipe=serialize_recipe(recipe),
        updated_inventory=[serialize_inventory(item) for item in updated],
    )

