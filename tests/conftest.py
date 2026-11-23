from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.threat import RadarStation, ThreatSignal  # noqa: F401
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_users(db_session: Session) -> dict[str, User]:
    admin = User(
        username="cmd_admin",
        email="admin@space-defense.org",
        full_name="Command Center Admin",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN.value,
    )
    alice = User(
        username="operator_alice",
        email="alice@radar-net.org",
        full_name="Alice Radar Operator",
        hashed_password=hash_password("AlicePass123!"),
        role=UserRole.USER.value,
    )
    bob = User(
        username="operator_bob",
        email="bob@radar-net.org",
        full_name="Bob Radar Operator",
        hashed_password=hash_password("BobPass123!"),
        role=UserRole.USER.value,
    )
    db_session.add_all([admin, alice, bob])
    db_session.commit()
    for usr in (admin, alice, bob):
        db_session.refresh(usr)
    return {"admin": admin, "alice": alice, "bob": bob}


def auth_header(client: TestClient, username: str, password: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
