from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.models.entities import InventoryBatch, StockChange
from app.services.inventory import calculate_status
from app.services.rate_limit import RateLimiter, limiter
from fastapi import HTTPException
from redis.exceptions import RedisError
import pytest
from app.core.config import Settings


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
    insecure = Settings(_env_file=None, environment="production", database_url="sqlite:///unsafe.db")
    with pytest.raises(RuntimeError) as exc:
        insecure.validate_for_startup()
    assert "SQLite" in str(exc.value)
    assert "微信" in str(exc.value)
    assert "Redis" in str(exc.value)

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


def test_household_invite_and_cross_household_isolation(client):
    assert client.get(
        "/api/v1/inventory",
        headers={"Authorization": "", "X-Household-Id": ""},
    ).status_code == 401
    owner_login = client.post(
        "/api/v1/auth/dev",
        json={"openid": "owner", "nickname": "家庭所有者", "dev_key": "test-dev-key"},
    ).json()
    member_login = client.post(
        "/api/v1/auth/dev",
        json={"openid": "member", "nickname": "家庭成员", "dev_key": "test-dev-key"},
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
        json={"openid": "lifecycle-owner", "nickname": "原所有者", "dev_key": "test-dev-key"},
    ).json()
    member = client.post(
        "/api/v1/auth/dev",
        json={"openid": "lifecycle-member", "nickname": "新所有者", "dev_key": "test-dev-key"},
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
        json={"openid": "logout-user", "nickname": "退出用户", "dev_key": "test-dev-key"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_account_deletion_erases_private_household(client, db_session):
    login = client.post(
        "/api/v1/auth/dev",
        json={"openid": "delete-user", "nickname": "待注销用户", "dev_key": "test-dev-key"},
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
        json={"openid": "delete-owner", "nickname": "所有者", "dev_key": "test-dev-key"},
    ).json()
    member = client.post(
        "/api/v1/auth/dev",
        json={"openid": "delete-member", "nickname": "成员", "dev_key": "test-dev-key"},
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
