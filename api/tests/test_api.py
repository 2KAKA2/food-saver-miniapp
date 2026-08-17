import base64
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.api.v1.endpoints.recipes import _normalize_result
from app.models.entities import InventoryBatch, StockChange, User
from app.schemas.api import RecipeGenerateRequest
from app.services import ai
from app.services.inventory import calculate_status
from app.services.rate_limit import RateLimiter, limiter
from fastapi import HTTPException
from redis.exceptions import RedisError
import pytest
from app.core.config import Settings, settings
from app.main import create_app


def inventory_payload(name="西红柿", quantity="3", days=1):
    today = date.today()
    return {
        "name": name,
        "category": "蔬菜",
        "quantity": quantity,
        "unit": "个",
        "location": "冷藏",
        "purchase_date": today.isoformat(),
        "expiry_date": (today + timedelta(days=days)).isoformat(),
        "note": "",
    }


def test_status_boundaries():
    today = date(2026, 8, 17)
    assert calculate_status(None, today) == ("normal", None)
    assert calculate_status(today - timedelta(days=1), today) == ("expired", -1)
    assert calculate_status(today, today) == ("today", 0)
    assert calculate_status(today + timedelta(days=3), today) == ("expiring", 3)
    assert calculate_status(today + timedelta(days=4), today) == ("normal", 4)


def test_memory_rate_limiter_rejects_excess_requests():
    limiter = RateLimiter()
    limiter.enforce("unit-test", "unique-rate-user", limit=2, window_seconds=60)
    limiter.enforce("unit-test", "unique-rate-user", limit=2, window_seconds=60)
    try:
        limiter.enforce("unit-test", "unique-rate-user", limit=2, window_seconds=60)
        assert False, "第三次请求应被限流"
    except HTTPException as exc:
        assert exc.status_code == 429
        assert "Retry-After" in exc.headers


def test_production_configuration_fails_closed():
    insecure = Settings(
        _env_file=None,
        environment="production",
        database_url="sqlite:///unsafe.db",
        require_redis=True,
        require_ai_key=True,
    )
    with pytest.raises(RuntimeError) as exc:
        insecure.validate_for_startup()
    assert "SQLite" in str(exc.value)
    assert "微信" in str(exc.value)
    assert "Redis" in str(exc.value)
    assert "AI" in str(exc.value)

    secure = Settings(
        _env_file=None,
        environment="production",
        database_url="mysql+pymysql://user:pass@mysql/db",
        redis_url="redis://:pass@redis:6379/0",
        wechat_app_id="wx-test",
        wechat_app_secret="server-only-secret",
        zhipu_api_key="ai-secret",
        allow_dev_login=False,
        seed_demo_data=False,
        allowed_hosts="api.example.com",
    )
    secure.validate_for_startup()

    cloudbase_single_instance = Settings(
        _env_file=None,
        environment="production",
        database_url="mysql+pymysql://user:pass@mysql/db",
        wechat_app_id="wx-test",
        wechat_app_secret="server-only-secret",
        allow_dev_login=False,
        seed_demo_data=False,
        allowed_hosts="food-saver-api",
    )
    cloudbase_single_instance.validate_for_startup()


def test_production_hides_interactive_api_documentation(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    application = create_app(seed_demo=False)
    assert application.docs_url is None
    assert application.redoc_url is None
    assert application.openapi_url is None


def test_login_records_current_legal_acceptance(client, db_session):
    user = db_session.scalar(select(User).where(User.openid == "dev:default-test-user"))
    assert user.legal_version == "2026-08-17"
    assert user.legal_accepted_at is not None

    stale = client.post(
        "/api/v1/auth/dev",
        json={
            "openid": "stale-legal-user",
            "nickname": "旧协议用户",
            "dev_key": "test-dev-key",
            "legal_version": "2026-01-01",
        },
    )
    assert stale.status_code == 409
    assert "重新阅读" in stale.json()["detail"]


def test_policy_update_revokes_existing_session(client, monkeypatch):
    monkeypatch.setattr(settings, "legal_version", "2026-08-18")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "重新阅读" in response.json()["detail"]


def test_health_checks_report_dependency_status(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "disabled"},
    }


def test_user_can_set_a_family_display_nickname(client):
    updated = client.put("/api/v1/auth/profile", json={"nickname": "小满"})
    assert updated.status_code == 200
    assert set(updated.json()) == {"id", "nickname"}
    assert updated.json()["nickname"] == "小满"
    assert client.get("/api/v1/auth/me").json()["user"]["nickname"] == "小满"
    assert client.put("/api/v1/auth/profile", json={"nickname": "   "}).status_code == 422


def test_readiness_fails_when_redis_is_unavailable(client, monkeypatch):
    class FailedRedis:
        def ping(self):
            raise RedisError("test outage")

    monkeypatch.setattr(limiter, "_redis", FailedRedis())
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "缓存与请求保护服务暂不可用"


def test_inventory_crud_and_dashboard(client):
    response = client.post("/api/v1/inventory", json=inventory_payload())
    assert response.status_code == 201
    item = response.json()
    assert item["status"] == "expiring"

    second = client.post("/api/v1/inventory", json=inventory_payload(quantity="2", days=8))
    assert second.status_code == 201
    listed = client.get("/api/v1/inventory").json()
    assert len(listed) == 2
    assert listed[0]["id"] == item["id"]

    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["inventory_count"] == 2
    assert dashboard["expiring_count"] == 1

    changed = inventory_payload(quantity="4", days=2)
    assert client.put(f"/api/v1/inventory/{item['id']}", json=changed).json()["quantity"] == "4.00"
    assert client.delete(f"/api/v1/inventory/{item['id']}").status_code == 204


def test_invalid_quantity_and_dates(client):
    bad = inventory_payload(quantity="0")
    assert client.post("/api/v1/inventory", json=bad).status_code == 422
    bad_date = inventory_payload()
    bad_date["expiry_date"] = (date.today() - timedelta(days=1)).isoformat()
    assert client.post("/api/v1/inventory", json=bad_date).status_code == 422


def test_fallback_recipe_and_atomic_cook(client, db_session):
    tomato = client.post("/api/v1/inventory", json=inventory_payload("西红柿", "3", 1)).json()
    egg = client.post("/api/v1/inventory", json=inventory_payload("鸡蛋", "4", 7)).json()
    recipe_response = client.post(
        "/api/v1/recipes/generate",
        json={"inventory_ids": [tomato["id"], egg["id"]], "servings": 2, "flavor": "家常", "max_minutes": 30},
    )
    assert recipe_response.status_code == 201
    recipe = recipe_response.json()
    assert recipe["source"] == "fallback"

    failed = client.post(
        f"/api/v1/recipes/{recipe['id']}/cook",
        json={"consumptions": [{"inventory_id": tomato["id"], "quantity": "2"}, {"inventory_id": egg["id"], "quantity": "99"}]},
        headers={"Idempotency-Key": "cook-failed-001"},
    )
    assert failed.status_code == 409
    assert db_session.get(InventoryBatch, tomato["id"]).quantity == Decimal("3.00")

    cooked = client.post(
        f"/api/v1/recipes/{recipe['id']}/cook",
        json={"consumptions": [{"inventory_id": tomato["id"], "quantity": "2"}, {"inventory_id": egg["id"], "quantity": "2"}]},
        headers={"Idempotency-Key": "cook-success-001"},
    )
    assert cooked.status_code == 200
    assert cooked.json()["recipe"]["status"] == "cooked"
    assert db_session.get(InventoryBatch, tomato["id"]).quantity == Decimal("1.00")
    cook_logs = db_session.scalar(
        select(func.count()).select_from(StockChange).where(StockChange.change_type == "cook")
    )
    assert cook_logs == 2
    repeated = client.post(
        f"/api/v1/recipes/{recipe['id']}/cook",
        json={"consumptions": [{"inventory_id": tomato["id"], "quantity": "2"}, {"inventory_id": egg["id"], "quantity": "2"}]},
        headers={"Idempotency-Key": "cook-success-001"},
    )
    assert repeated.status_code == 200
    assert db_session.get(InventoryBatch, tomato["id"]).quantity == Decimal("1.00")
    assert client.post(
        f"/api/v1/recipes/{recipe['id']}/cook",
        json={"consumptions": [{"inventory_id": tomato["id"], "quantity": "1"}]},
        headers={"Idempotency-Key": "cook-different-002"},
    ).status_code == 409


def test_image_fallback_does_not_write_inventory(client):
    before = len(client.get("/api/v1/inventory").json())
    response = client.post(
        "/api/v1/ai/recognize-ingredients",
        files={"file": ("food.png", b"\x89PNG\r\n\x1a\nminimal", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert len(client.get("/api/v1/inventory").json()) == before


def test_base64_image_fallback_does_not_write_inventory(client):
    before = len(client.get("/api/v1/inventory").json())
    encoded = base64.b64encode(b"\x89PNG\r\n\x1a\nminimal").decode("ascii")
    response = client.post(
        "/api/v1/ai/recognize-ingredients/base64",
        json={"image_base64": encoded, "content_type": "image/png"},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert len(client.get("/api/v1/inventory").json()) == before


def test_base64_image_rejects_invalid_encoding_or_spoofed_content(client):
    invalid = client.post(
        "/api/v1/ai/recognize-ingredients/base64",
        json={"image_base64": "not-base64***"},
    )
    assert invalid.status_code == 400

    encoded = base64.b64encode(b"\x89PNG\r\n\x1a\nminimal").decode("ascii")
    spoofed = client.post(
        "/api/v1/ai/recognize-ingredients/base64",
        json={"image_base64": encoded, "content_type": "image/jpeg"},
    )
    assert spoofed.status_code == 415


def test_image_upload_rejects_invalid_or_spoofed_content(client):
    invalid = client.post(
        "/api/v1/ai/recognize-ingredients",
        files={"file": ("food.png", b"not-a-real-image", "image/png")},
    )
    assert invalid.status_code == 400

    spoofed = client.post(
        "/api/v1/ai/recognize-ingredients",
        files={"file": ("food.jpg", b"\x89PNG\r\n\x1a\nminimal", "image/jpeg")},
    )
    assert spoofed.status_code == 415


def test_recipe_model_output_cannot_spoof_or_overdraw_inventory():
    batch = InventoryBatch(
        id=77,
        household_id=1,
        created_by_user_id=1,
        name="西红柿",
        category="蔬菜",
        quantity=Decimal("3"),
        unit="个",
        location="冷藏",
    )
    payload = RecipeGenerateRequest(
        inventory_ids=[77, 77], servings=2, flavor=" 家常 ", max_minutes=30
    )
    result = _normalize_result(
        {
            "title": {"不可信": True},
            "cook_time_minutes": "not-a-number",
            "difficulty": {"level": "hard"},
            "ingredients": [
                {
                    "inventory_id": 77,
                    "name": "伪造名称",
                    "quantity": "999",
                    "unit": "公斤",
                    "available": False,
                },
                {
                    "inventory_id": 77,
                    "name": "重复食材",
                    "quantity": "1",
                    "unit": "份",
                },
                {
                    "inventory_id": 999,
                    "name": "不存在的批次",
                    "quantity": "1",
                    "unit": "份",
                },
                {"inventory_id": None, "name": "非法负数", "quantity": "-1", "unit": "份"},
            ],
            "missing_ingredients": "not-a-list",
            "steps": {"step": "not-a-list"},
            "source": "ai",
        },
        {77: batch},
        payload,
    )

    assert payload.inventory_ids == [77]
    assert payload.flavor == "家常"
    assert result["title"] == "AI 推荐菜谱"
    assert result["cook_time_minutes"] == 20
    assert result["difficulty"] == "简单"
    assert result["steps"] == ["清洗并处理食材。", "依次烹饪至熟透。", "调味后装盘。"]
    valid_items = [item for item in result["ingredients"] if item["inventory_id"] == 77]
    assert len(valid_items) == 1
    assert valid_items[0]["name"] == "西红柿"
    assert valid_items[0]["unit"] == "个"
    assert Decimal(valid_items[0]["quantity"]) == Decimal("3")
    assert valid_items[0]["available"] is True
    assert any(
        item["name"] == "不存在的批次"
        and item["inventory_id"] is None
        and item["available"] is False
        for item in result["ingredients"]
    )


def test_vision_model_output_is_validated_and_capped(monkeypatch):
    model_items = [
        {
            "name": " 西红柿 ",
            "category": " 蔬菜 ",
            "quantity": "2",
            "unit": " 个 ",
            "confidence": 0.9,
        },
        {
            "name": "非法数量",
            "category": "其他",
            "quantity": "-1",
            "unit": "份",
            "confidence": 0.5,
        },
        *[
            {
                "name": f"食材{i}",
                "category": "其他",
                "quantity": "1",
                "unit": "份",
                "confidence": 0.5,
            }
            for i in range(25)
        ],
    ]
    monkeypatch.setattr(ai, "_zhipu_chat", lambda *args, **kwargs: model_items)

    result = ai.recognize_ingredients(b"image-data", "image/png")

    assert result["source"] == "ai"
    assert len(result["items"]) == 19
    assert result["items"][0]["name"] == "西红柿"
    assert result["items"][0]["category"] == "蔬菜"
    assert result["items"][0]["unit"] == "个"
    assert all(item["name"] != "非法数量" for item in result["items"])


def test_household_invite_and_cross_household_isolation(client):
    assert client.get(
        "/api/v1/inventory",
        headers={"Authorization": "", "X-Household-Id": ""},
    ).status_code == 401
    owner_login = client.post(
        "/api/v1/auth/dev",
        json={"openid": "owner", "nickname": "家庭所有者", "dev_key": "test-dev-key", "legal_version": "2026-08-17"},
    ).json()
    member_login = client.post(
        "/api/v1/auth/dev",
        json={"openid": "member", "nickname": "家庭成员", "dev_key": "test-dev-key", "legal_version": "2026-08-17"},
    ).json()
    owner_household = owner_login["households"][0]["id"]
    member_household = member_login["households"][0]["id"]
    owner_headers = {
        "Authorization": f"Bearer {owner_login['access_token']}",
        "X-Household-Id": str(owner_household),
    }
    member_headers = {
        "Authorization": f"Bearer {member_login['access_token']}",
        "X-Household-Id": str(member_household),
    }

    created = client.post(
        "/api/v1/inventory",
        json=inventory_payload("家庭共享西红柿", "3", 2),
        headers=owner_headers,
    )
    assert created.status_code == 201
    assert client.get("/api/v1/inventory", headers=member_headers).json() == []

    forbidden_headers = {**member_headers, "X-Household-Id": str(owner_household)}
    assert client.get("/api/v1/inventory", headers=forbidden_headers).status_code == 403

    invite = client.post(
        "/api/v1/households/current/invites",
        json={"expires_in_hours": 24, "max_uses": 1},
        headers=owner_headers,
    )
    assert invite.status_code == 201
    join = client.post(
        "/api/v1/households/join",
        json={"invite_code": invite.json()["invite_code"]},
        headers={"Authorization": member_headers["Authorization"]},
    )
    assert join.status_code == 200
    assert client.post(
        "/api/v1/households/join",
        json={"invite_code": invite.json()["invite_code"]},
        headers={"Authorization": member_headers["Authorization"]},
    ).status_code == 404
    shared_headers = {**member_headers, "X-Household-Id": str(owner_household)}
    assert client.get("/api/v1/inventory", headers=shared_headers).json()[0]["name"] == "家庭共享西红柿"
    assert client.post(
        "/api/v1/households/current/invites",
        json={"expires_in_hours": 24, "max_uses": 1},
        headers=shared_headers,
    ).status_code == 403


def test_household_invite_revoke_transfer_and_leave(client):
    owner = client.post(
        "/api/v1/auth/dev",
        json={"openid": "lifecycle-owner", "nickname": "原所有者", "dev_key": "test-dev-key", "legal_version": "2026-08-17"},
    ).json()
    member = client.post(
        "/api/v1/auth/dev",
        json={"openid": "lifecycle-member", "nickname": "新所有者", "dev_key": "test-dev-key", "legal_version": "2026-08-17"},
    ).json()
    household_id = owner["households"][0]["id"]
    owner_headers = {
        "Authorization": f"Bearer {owner['access_token']}",
        "X-Household-Id": str(household_id),
    }
    member_auth = {"Authorization": f"Bearer {member['access_token']}"}

    revoked_invite = client.post(
        "/api/v1/households/current/invites",
        json={"expires_in_hours": 1, "max_uses": 1},
        headers=owner_headers,
    ).json()
    assert client.delete(
        f"/api/v1/households/current/invites/{revoked_invite['invite_id']}",
        headers=owner_headers,
    ).status_code == 204
    assert client.post(
        "/api/v1/households/join",
        json={"invite_code": revoked_invite["invite_code"]},
        headers=member_auth,
    ).status_code == 404

    invite = client.post(
        "/api/v1/households/current/invites",
        json={"expires_in_hours": 1, "max_uses": 1},
        headers=owner_headers,
    ).json()
    assert client.post(
        "/api/v1/households/join",
        json={"invite_code": invite["invite_code"]},
        headers=member_auth,
    ).status_code == 200

    assert client.put(
        "/api/v1/households/current", json={"name": "共同的家"}, headers=owner_headers
    ).json()["name"] == "共同的家"
    assert client.put(
        "/api/v1/households/current", json={"name": "   "}, headers=owner_headers
    ).status_code == 422

    transferred = client.post(
        "/api/v1/households/current/transfer",
        json={"new_owner_user_id": member["user"]["id"]},
        headers=owner_headers,
    )
    assert transferred.status_code == 200
    assert transferred.json()["role"] == "member"
    assert client.post(
        "/api/v1/households/current/invites",
        json={"expires_in_hours": 1, "max_uses": 1},
        headers=owner_headers,
    ).status_code == 403

    new_owner_headers = {**member_auth, "X-Household-Id": str(household_id)}
    assert client.get(
        "/api/v1/households/current", headers=new_owner_headers
    ).json()["role"] == "owner"
    assert client.post(
        "/api/v1/households/current/leave", headers=owner_headers
    ).status_code == 204
    assert client.get(
        "/api/v1/households/current", headers=new_owner_headers
    ).json()["member_count"] == 1


def test_logout_revokes_session(client):
    login = client.post(
        "/api/v1/auth/dev",
        json={"openid": "logout-user", "nickname": "退出用户", "dev_key": "test-dev-key", "legal_version": "2026-08-17"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_account_deletion_erases_private_household(client, db_session):
    login = client.post(
        "/api/v1/auth/dev",
        json={"openid": "delete-user", "nickname": "待注销用户", "dev_key": "test-dev-key", "legal_version": "2026-08-17"},
    ).json()
    household_id = login["households"][0]["id"]
    headers = {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Household-Id": str(household_id),
    }
    assert client.post(
        "/api/v1/inventory", json=inventory_payload("注销测试食材"), headers=headers
    ).status_code == 201
    assert client.request(
        "DELETE",
        "/api/v1/auth/account",
        json={"confirmation": "注销账号"},
        headers=headers,
    ).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert db_session.scalar(
        select(func.count()).select_from(InventoryBatch).where(
            InventoryBatch.household_id == household_id
        )
    ) == 0


def test_account_deletion_requires_owner_transfer(client):
    owner = client.post(
        "/api/v1/auth/dev",
        json={"openid": "delete-owner", "nickname": "所有者", "dev_key": "test-dev-key", "legal_version": "2026-08-17"},
    ).json()
    member = client.post(
        "/api/v1/auth/dev",
        json={"openid": "delete-member", "nickname": "成员", "dev_key": "test-dev-key", "legal_version": "2026-08-17"},
    ).json()
    household_id = owner["households"][0]["id"]
    owner_headers = {
        "Authorization": f"Bearer {owner['access_token']}",
        "X-Household-Id": str(household_id),
    }
    invite = client.post(
        "/api/v1/households/current/invites",
        json={"expires_in_hours": 1, "max_uses": 1},
        headers=owner_headers,
    ).json()
    client.post(
        "/api/v1/households/join",
        json={"invite_code": invite["invite_code"]},
        headers={"Authorization": f"Bearer {member['access_token']}"},
    )
    response = client.request(
        "DELETE",
        "/api/v1/auth/account",
        json={"confirmation": "注销账号"},
        headers=owner_headers,
    )
    assert response.status_code == 409
    assert "转让" in response.json()["detail"]
