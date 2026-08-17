import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, status
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
from app.services.ai import fallback_recipe, generate_recipe
from app.services.auth import HouseholdContext, get_household_context
from app.services.inventory import calculate_status, inventory_sort_key, serialize_inventory
from app.services.rate_limit import ai_rate_limit
from app.services.auth import sha256_token


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
    used_inventory_ids: set[int] = set()
    raw_ingredients = result.get("ingredients", [])
    if not isinstance(raw_ingredients, list):
        raw_ingredients = []
    for raw in raw_ingredients[:20]:
        try:
            item = RecipeIngredient.model_validate(raw)
        except ValidationError:
            continue
        if item.inventory_id is not None:
            batch = valid_batches.get(item.inventory_id)
            if not batch:
                item.inventory_id = None
                item.available = False
            elif item.inventory_id in used_inventory_ids:
                continue
            else:
                used_inventory_ids.add(item.inventory_id)
                item.name = batch.name
                item.unit = batch.unit
                item.available = True
                if item.quantity > Decimal(batch.quantity):
                    item.quantity = Decimal(batch.quantity)
        else:
            item.available = False
        ingredients.append(item)
    missing = []
    raw_missing = result.get("missing_ingredients", [])
    if not isinstance(raw_missing, list):
        raw_missing = []
    for raw in raw_missing[:20]:
        try:
            missing.append(MissingIngredient.model_validate(raw))
        except ValidationError:
            continue
    raw_steps = result.get("steps", [])
    if not isinstance(raw_steps, list):
        raw_steps = []
    steps = [step.strip()[:500] for step in raw_steps[:20] if isinstance(step, str) and step.strip()]
    if not steps:
        steps = ["清洗并处理食材。", "依次烹饪至熟透。", "调味后装盘。"]
    raw_title = result.get("title")
    title = raw_title.strip()[:120] if isinstance(raw_title, str) and raw_title.strip() else "AI 推荐菜谱"
    raw_difficulty = result.get("difficulty")
    difficulty = (
        raw_difficulty.strip()[:20]
        if isinstance(raw_difficulty, str) and raw_difficulty.strip()
        else "简单"
    )
    try:
        cook_time = int(result.get("cook_time_minutes", 20))
    except (TypeError, ValueError, OverflowError):
        cook_time = 20
    return {
        "title": title,
        "servings": payload.servings,
        "cook_time_minutes": max(5, min(cook_time, payload.max_minutes)),
        "difficulty": difficulty,
        "ingredients": [item.model_dump(mode="json") for item in ingredients],
        "missing_ingredients": [item.model_dump(mode="json") for item in missing],
        "steps": steps,
        "source": "ai" if result.get("source") == "ai" else "fallback",
    }


@router.post(
    "/generate",
    response_model=RecipeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ai_rate_limit)],
)
def create_recipe(
    payload: RecipeGenerateRequest,
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    query = select(InventoryBatch).where(
        InventoryBatch.household_id == context.household.id,
        InventoryBatch.quantity > 0,
    )
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
    if not any(item["inventory_id"] is not None for item in result["ingredients"]):
        result = _normalize_result(
            fallback_recipe(batches, payload.servings, payload.max_minutes),
            {item.id: item for item in batches},
            payload,
        )
    recipe = Recipe(
        household_id=context.household.id,
        created_by_user_id=context.user.id,
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
def list_recipes(
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    recipes = db.scalars(
        select(Recipe).where(Recipe.household_id == context.household.id).order_by(
            Recipe.created_at.desc(), Recipe.id.desc()
        )
    ).all()
    return [serialize_recipe(item) for item in recipes]


@router.get("/{recipe_id}", response_model=RecipeOut)
def recipe_detail(
    recipe_id: int,
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    recipe = db.get(Recipe, recipe_id)
    if not recipe or recipe.household_id != context.household.id:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return serialize_recipe(recipe)


@router.post("/{recipe_id}/cook", response_model=CookOut)
def cook_recipe(
    recipe_id: int,
    payload: CookRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=200),
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.household_id == context.household.id)
        .with_for_update()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    key_hash = sha256_token(idempotency_key.strip())
    if recipe.status == "cooked":
        if recipe.cook_idempotency_key_hash == key_hash and recipe.cook_result_json:
            return CookOut.model_validate(json.loads(recipe.cook_result_json))
        raise HTTPException(status_code=409, detail="该菜谱已经确认制作")

    merged: dict[int, Decimal] = {}
    for item in payload.consumptions:
        merged[item.inventory_id] = merged.get(item.inventory_id, Decimal("0")) + item.quantity

    batches = {
        item.id: item
        for item in db.scalars(
            select(InventoryBatch).where(
                InventoryBatch.household_id == context.household.id,
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
                household_id=context.household.id,
                actor_user_id=context.user.id,
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
    recipe.cook_idempotency_key_hash = key_hash
    db.flush()
    for batch in updated:
        db.refresh(batch)
    result = CookOut(
        recipe=serialize_recipe(recipe),
        updated_inventory=[serialize_inventory(item) for item in updated],
    )
    recipe.cook_result_json = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
    db.commit()
    return result
