import base64
import json
import re
from decimal import Decimal

import httpx

from app.core.config import settings
from app.models.entities import InventoryBatch


ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


def _extract_json(text: str):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_candidates = [pos for pos in (cleaned.find("{"), cleaned.find("[")) if pos >= 0]
        if not start_candidates:
            raise
        start = min(start_candidates)
        end = max(cleaned.rfind("}"), cleaned.rfind("]"))
        return json.loads(cleaned[start : end + 1])


def _zhipu_chat(model: str, messages: list[dict], timeout: float = 45.0):
    if not settings.zhipu_api_key:
        raise RuntimeError("未配置智谱 API Key")
    response = httpx.post(
        ZHIPU_URL,
        headers={
            "Authorization": f"Bearer {settings.zhipu_api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages, "temperature": 0.3},
        timeout=timeout,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _extract_json(content)


def _suggested_quantity(batch: InventoryBatch) -> Decimal:
    available = Decimal(batch.quantity)
    common = {
        "g": Decimal("150"),
        "克": Decimal("150"),
        "kg": Decimal("0.2"),
        "千克": Decimal("0.2"),
        "斤": Decimal("0.5"),
        "ml": Decimal("200"),
        "毫升": Decimal("200"),
    }.get(batch.unit.lower(), Decimal("1"))
    return min(available, common)


def fallback_recipe(batches: list[InventoryBatch], servings: int, max_minutes: int) -> dict:
    selected = batches[:4]
    names = "、".join(item.name for item in selected) or "时令食材"
    ingredients = [
        {
            "inventory_id": item.id,
            "name": item.name,
            "quantity": str(_suggested_quantity(item)),
            "unit": item.unit,
            "available": True,
        }
        for item in selected
    ]
    return {
        "title": f"临期优先·{names}家常小炒",
        "servings": servings,
        "cook_time_minutes": min(max_minutes, 25),
        "difficulty": "简单",
        "ingredients": ingredients,
        "missing_ingredients": [
            {"name": "食用油", "quantity": "1", "unit": "勺"},
            {"name": "盐", "quantity": "1", "unit": "小撮"},
        ],
        "steps": [
            "将食材清洗干净，根据成熟速度切成合适大小。",
            "锅中加入少量食用油，先放入较难熟的食材翻炒。",
            "依次加入其余食材，翻炒至全部熟透。",
            "加入少量盐调味，装盘后趁热食用。",
        ],
        "source": "fallback",
    }


def generate_recipe(batches: list[InventoryBatch], servings: int, flavor: str, max_minutes: int) -> dict:
    if not batches:
        return fallback_recipe([], servings, max_minutes)
    inventory = [
        {
            "inventory_id": item.id,
            "name": item.name,
            "quantity": str(item.quantity),
            "unit": item.unit,
            "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
        }
        for item in batches
    ]
    prompt = f"""
你是家庭食材管理助手。请基于库存生成一道真实可做的菜，优先消耗临期食材。
库存：{json.dumps(inventory, ensure_ascii=False)}
人数：{servings}，口味：{flavor}，最长时间：{max_minutes}分钟。
只返回 JSON 对象，字段必须为：title、servings、cook_time_minutes、difficulty、ingredients、missing_ingredients、steps。
ingredients 每项包含 inventory_id、name、quantity、unit、available；库存食材必须使用正确 inventory_id，数量不得超过库存。
missing_ingredients 每项包含 name、quantity、unit；steps 是字符串数组。
""".strip()
    try:
        result = _zhipu_chat(
            settings.zhipu_chat_model,
            [
                {"role": "system", "content": "你是严谨的中式家常菜谱助手，只输出合法 JSON。"},
                {"role": "user", "content": prompt},
            ],
        )
        result["source"] = "ai"
        result["servings"] = servings
        return result
    except Exception:
        return fallback_recipe(batches, servings, max_minutes)


def recognize_ingredients(image_bytes: bytes, content_type: str) -> dict:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{content_type};base64,{encoded}"
    prompt = (
        "识别图片中的可食用食材，只返回 JSON 数组。每项字段为 name、category、quantity、unit、confidence。"
        "quantity 是估计数量，无法判断时填 1；不要推测保质期。"
    )
    try:
        items = _zhipu_chat(
            settings.zhipu_vision_model,
            [
                {"role": "system", "content": "你是食材图片识别助手，只输出合法 JSON。"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        )
        if isinstance(items, dict):
            items = items.get("items", [])
        return {"source": "ai", "items": items, "message": "识别完成，请确认后再加入库存"}
    except Exception:
        return {
            "source": "fallback",
            "items": [
                {"name": "西红柿", "category": "蔬菜", "quantity": 2, "unit": "个", "confidence": 0.6},
                {"name": "鸡蛋", "category": "蛋奶", "quantity": 3, "unit": "个", "confidence": 0.55},
            ],
            "message": "AI 暂不可用，已返回演示识别结果，请修改确认",
        }

