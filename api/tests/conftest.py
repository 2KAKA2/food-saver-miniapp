import os

os.environ["ZHIPU_API_KEY"] = ""
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["ALLOW_DEV_LOGIN"] = "true"
os.environ["DEV_LOGIN_SECRET"] = "test-dev-key"
os.environ["ALLOWED_HOSTS"] = "testserver,localhost"
os.environ["LOGIN_RATE_LIMIT"] = "1000"
os.environ["AI_RATE_LIMIT"] = "1000"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import create_app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)
    with TestingSession() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    app = create_app(seed_demo=False)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        login = test_client.post(
            "/api/v1/auth/dev",
            json={"openid": "default-test-user", "nickname": "测试用户", "dev_key": "test-dev-key"},
        )
        assert login.status_code == 200
        data = login.json()
        test_client.headers.update(
            {
                "Authorization": f"Bearer {data['access_token']}",
                "X-Household-Id": str(data["households"][0]["id"]),
            }
        )
        yield test_client
