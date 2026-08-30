import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

from app.core.enums import UserRole
from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.security import create_access_token

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    user = User(
        user_code="ADM-001",
        name="Admin User",
        email="admin@example.com",
        mobile="+919000000001",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def staff_user(db_session):
    user = User(
        user_code="STF-001",
        name="Staff User",
        email="staff@example.com",
        mobile="+919000000002",
        role=UserRole.STAFF,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_staff_user(db_session):
    user = User(
        user_code="STF-002",
        name="Other Staff",
        email="otherstaff@example.com",
        mobile="+919000000003",
        role=UserRole.STAFF,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_admin_user(db_session):
    user = User(
        user_code="ADM-002",
        name="Second Admin",
        email="secondadmin@example.com",
        mobile="+919000000004",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_token(user: User) -> str:
    return create_access_token(
        subject=user.id,
        role=user.role.value,
        actor_type=user.role.value,
        email=user.email,
        mobile=user.mobile,
    )


def request_otp_for_delete(db_session, identifier: str):
    auth_service = AuthService(db_session)
    _, _, _, _, raw_otp = auth_service.request_admin_otp(
        identifier=identifier,
        purpose="DELETE_ACCOUNT",
    )
    return raw_otp


def test_admin_can_update_any_staff_account(client, admin_user, staff_user):
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}

    response = client.patch(
        f"/api/v1/admin/account/{staff_user.id}",
        json={"name": "Updated Staff Name"},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "User updated successfully."


def test_admin_cannot_update_another_admin_account(client, admin_user, second_admin_user):
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}

    response = client.patch(
        f"/api/v1/admin/account/{second_admin_user.id}",
        json={"name": "Attempted Update"},
        headers=auth_header,
    )

    assert response.status_code == 403


def test_staff_can_update_only_own_account(client, staff_user, second_staff_user):
    auth_header = {"Authorization": f"Bearer {make_token(staff_user)}"}

    own_response = client.patch(
        f"/api/v1/admin/account/{staff_user.id}",
        json={"name": "My Updated Name"},
        headers=auth_header,
    )
    assert own_response.status_code == 200

    other_response = client.patch(
        f"/api/v1/admin/account/{second_staff_user.id}",
        json={"name": "Forbidden Update"},
        headers=auth_header,
    )
    assert other_response.status_code == 403


def test_staff_cannot_update_admin_account(client, staff_user, admin_user):
    auth_header = {"Authorization": f"Bearer {make_token(staff_user)}"}

    response = client.patch(
        f"/api/v1/admin/account/{admin_user.id}",
        json={"name": "Blocked"},
        headers=auth_header,
    )

    assert response.status_code == 403


def test_admin_can_deactivate_staff_account(client, admin_user, staff_user, db_session):
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}
    raw_otp = request_otp_for_delete(db_session, admin_user.email)

    response = client.request(
        "DELETE",
        f"/api/v1/admin/account/{staff_user.id}",
        json={"identifier": admin_user.email, "otp": raw_otp},
        headers={**auth_header, "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully."
    assert db_session.get(User, staff_user.id).is_active is False


def test_admin_can_deactivate_own_account(client, admin_user, db_session):
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}
    raw_otp = request_otp_for_delete(db_session, admin_user.email)

    response = client.request(
        "DELETE",
        f"/api/v1/admin/account/{admin_user.id}",
        json={"identifier": admin_user.email, "otp": raw_otp},
        headers={**auth_header, "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert db_session.get(User, admin_user.id).is_active is False


def test_staff_cannot_deactivate_any_account(client, staff_user, admin_user, db_session):
    auth_header = {"Authorization": f"Bearer {make_token(staff_user)}"}
    raw_otp = request_otp_for_delete(db_session, staff_user.email)

    response = client.request(
        "DELETE",
        f"/api/v1/admin/account/{staff_user.id}",
        json={"identifier": staff_user.email, "otp": raw_otp},
        headers={**auth_header, "Content-Type": "application/json"},
    )

    assert response.status_code == 403
