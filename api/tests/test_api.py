from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.models.entities import InventoryBatch, StockChange
from app.services.inventory import calculate_status


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
    )
    assert failed.status_code == 409
    assert db_session.get(InventoryBatch, tomato["id"]).quantity == Decimal("3.00")

    cooked = client.post(
        f"/api/v1/recipes/{recipe['id']}/cook",
        json={"consumptions": [{"inventory_id": tomato["id"], "quantity": "2"}, {"inventory_id": egg["id"], "quantity": "2"}]},
    )
    assert cooked.status_code == 200
    assert cooked.json()["recipe"]["status"] == "cooked"
    assert db_session.get(InventoryBatch, tomato["id"]).quantity == Decimal("1.00")
    cook_logs = db_session.scalar(
        select(func.count()).select_from(StockChange).where(StockChange.change_type == "cook")
    )
    assert cook_logs == 2
    assert client.post(
        f"/api/v1/recipes/{recipe['id']}/cook",
        json={"consumptions": [{"inventory_id": tomato["id"], "quantity": "1"}]},
    ).status_code == 409


def test_image_fallback_does_not_write_inventory(client):
    before = len(client.get("/api/v1/inventory").json())
    response = client.post(
        "/api/v1/ai/recognize-ingredients",
        files={"file": ("food.png", b"not-a-real-image", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert len(client.get("/api/v1/inventory").json()) == before


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


def test_logout_revokes_session(client):
    login = client.post(
        "/api/v1/auth/dev",
        json={"openid": "logout-user", "nickname": "退出用户", "dev_key": "test-dev-key"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
