import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.enums import UserRole
from app.db.database import get_db
from app.main import app
from app.models.auth_session import AuthSession
from app.models.base import Base
from app.models.customer import Customer
from app.models.room import Room
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.visitor import Visitor
from app.utils.security import (
    create_access_token,
)

# Enable JSONB support in SQLite in-memory test database
compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create clean database tables for each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Yield a database session for test setup and assertions."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden database dependency."""
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
def test_user(db_session) -> User:
    """Create a verified Admin test user."""
    user = User(
        user_code="USR-TEST01",
        name="Admin Tester",
        email="ppsdev6@gmail.com",
        mobile="+919876543210",
        profile_pic="https://images.unsplash.com/photo-admin.jpg",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_user(db_session) -> User:
    """Create a second Admin test user."""
    user = User(
        user_code="USR-TEST02",
        name="Staff Tester",
        email="progtesting01@gmail.com",
        mobile="+919876543211",
        role=UserRole.STAFF,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_customer(db_session) -> Customer:
    """Create an existing test Customer."""
    customer = Customer(
        customer_code="CUS-TEST01",
        name="John Traveler",
        email="ppsdev6@gmail.com",
        mobile="+919811122233",
        profile_pic="https://images.unsplash.com/photo-john.jpg",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def make_mock_google_id_token(email: str, name: str, picture: str | None = None) -> str:
    """Helper to generate mock Google ID token JWT."""
    payload = {
        "sub": "google-user-987654",
        "email": email,
        "name": name,
        "picture": picture or "https://lh3.googleusercontent.com/a/mock-pic.jpg",
        "email_verified": True,
        "aud": "mock-google-client-id",
        "iss": "https://accounts.google.com",
    }
    return jwt.encode(payload, "google-mock-secret", algorithm="HS256")


# ── TEST CASES ─────────────────────────────────────────────────────────

def test_1_admin_pure_otp_login(client: TestClient, test_user: User):
    """1. Test Admin pure OTP request and verification login flow."""
    req_res = client.post(
        "/api/v1/admin/auth/otp/request",
        json={"identifier": test_user.email},
    )
    assert req_res.status_code == 200
    otp = req_res.json()["data"]["dev_otp"]
    assert otp is not None
    assert len(otp) == 6

    verify_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": otp},
    )
    assert verify_res.status_code == 200
    res_json = verify_res.json()
    assert res_json["success"] is True
    data = res_json["data"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 15 * 60
    assert data["user"]["email"] == test_user.email
    assert data["user"]["profile_pic"] == test_user.profile_pic
    assert "refresh_token" not in data

    assert settings.REFRESH_COOKIE_NAME in verify_res.cookies


def test_2_customer_pure_otp_login_and_autoregistration(client: TestClient, db_session):
    """2. Test Customer OTP flow with auto-registration for a new traveler."""
    new_mobile = "+919988776655"
    req_res = client.post(
        "/api/v1/enduser/auth/otp/request",
        json={"identifier": new_mobile},
    )
    assert req_res.status_code == 200
    otp = req_res.json()["data"]["dev_otp"]

    verify_res = client.post(
        "/api/v1/enduser/auth/otp/verify",
        json={"identifier": new_mobile, "otp": otp, "name": "Alice Explorer"},
    )
    assert verify_res.status_code == 200
    data = verify_res.json()["data"]
    assert "access_token" in data
    assert data["customer"]["name"] == "Alice Explorer"
    assert data["customer"]["mobile"] == new_mobile
    assert settings.REFRESH_COOKIE_NAME in verify_res.cookies

    customer = db_session.query(Customer).filter_by(mobile=new_mobile).first()
    assert customer is not None
    assert customer.customer_code.startswith("CUS-")


def test_3_customer_visitor_telemetry_linking(client: TestClient, db_session):
    """3. Test linking anonymous visitor telemetry to customer upon OTP verification."""
    visitor = Visitor(visitor_code="VIS-ANON01", fingerprint="fp-abc-123", lead_score=20)
    db_session.add(visitor)
    db_session.commit()
    db_session.refresh(visitor)

    customer_email = "explorer@travel.com"
    req_res = client.post(
        "/api/v1/enduser/auth/otp/request",
        json={"identifier": customer_email, "visitor_id": str(visitor.id)},
    )
    otp = req_res.json()["data"]["dev_otp"]

    verify_res = client.post(
        "/api/v1/enduser/auth/otp/verify",
        json={
            "identifier": customer_email,
            "otp": otp,
            "name": "Bob Tourist",
            "visitor_id": str(visitor.id),
        },
    )
    assert verify_res.status_code == 200
    cust_id = uuid.UUID(verify_res.json()["data"]["customer"]["id"])

    db_session.refresh(visitor)
    assert visitor.customer_id == cust_id


def test_4_access_token_expiration(client: TestClient, test_user: User):
    """4. Test that an expired 15-minute access token is rejected with 401."""
    expired_token = create_access_token(
        subject=test_user.id,
        role=test_user.role.value,
        actor_type="USER",
        email=test_user.email,
        expires_delta=timedelta(minutes=-5),
    )

    response = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "Invalid or expired access token" in response.json()["message"]


def test_5_successful_refresh(client: TestClient, test_user: User):
    """5. Test successful token refresh using HttpOnly cookie."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    assert login_res.status_code == 200

    refresh_res = client.post("/api/v1/sessions/refresh", cookies=login_res.cookies)
    assert refresh_res.status_code == 200
    data = refresh_res.json()["data"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 15 * 60


def test_6_refresh_token_rotation(client: TestClient, test_user: User):
    """6. Test that a new refresh token is issued upon refresh."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    old_cookie_val = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    refresh_res = client.post("/api/v1/sessions/refresh", cookies=login_res.cookies)
    assert refresh_res.status_code == 200
    new_cookie_val = refresh_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    assert new_cookie_val is not None
    assert new_cookie_val != old_cookie_val


def test_7_old_refresh_token_rejected_after_rotation(client: TestClient, test_user: User):
    """7. Test that old refresh token is invalidated after rotation."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    old_cookies = dict(login_res.cookies)

    assert client.post("/api/v1/sessions/refresh", cookies=old_cookies).status_code == 200
    assert client.post("/api/v1/sessions/refresh", cookies=old_cookies).status_code == 401


def test_8_refresh_session_revoked(client: TestClient, test_user: User, db_session):
    """8. Test that manually revoked refresh sessions are rejected."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    cookies = dict(login_res.cookies)

    session = db_session.query(AuthSession).filter_by(user_id=test_user.id).first()
    session.revoked_at = datetime.now(timezone.utc)
    db_session.commit()

    assert client.post("/api/v1/sessions/refresh", cookies=cookies).status_code == 401


def test_9_refresh_session_expired_after_30_days(client: TestClient, test_user: User, db_session):
    """9. Test that refresh sessions older than 30 days are rejected."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    cookies = dict(login_res.cookies)

    session = db_session.query(AuthSession).filter_by(user_id=test_user.id).first()
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()

    res = client.post("/api/v1/sessions/refresh", cookies=cookies)
    assert res.status_code == 401
    assert "maximum 30-day limit reached" in res.json()["message"]


def test_10_refresh_session_rejected_after_24_hours_inactivity(
    client: TestClient, test_user: User, db_session
):
    """10. Test that refresh session is rejected if inactive for > 24 hours."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    cookies = dict(login_res.cookies)

    session = db_session.query(AuthSession).filter_by(user_id=test_user.id).first()
    session.last_used_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db_session.commit()

    res = client.post("/api/v1/sessions/refresh", cookies=cookies)
    assert res.status_code == 401
    assert "24 hours of inactivity" in res.json()["message"]


def test_11_active_user_can_continue_refreshing(client: TestClient, test_user: User):
    """11. Test that an active user can refresh multiple times sequentially."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    current_cookies = login_res.cookies

    for _ in range(5):
        res = client.post("/api/v1/sessions/refresh", cookies=current_cookies)
        assert res.status_code == 200
        current_cookies = res.cookies


def test_12_absolute_expiration_does_not_extend_after_refresh(
    client: TestClient, test_user: User, db_session
):
    """12. Test that the original 30-day absolute expiration deadline is strictly preserved across rotations."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    initial_session = (
        db_session.query(AuthSession)
        .filter_by(user_id=test_user.id)
        .order_by(AuthSession.created_at.desc())
        .first()
    )
    original_expires_at = initial_session.expires_at

    refresh_res = client.post("/api/v1/sessions/refresh", cookies=login_res.cookies)
    assert refresh_res.status_code == 200

    new_session = (
        db_session.query(AuthSession)
        .filter_by(user_id=test_user.id, revoked_at=None)
        .first()
    )
    assert new_session.expires_at == original_expires_at


def test_13_logout(client: TestClient, test_user: User, db_session):
    """13. Test that logout revokes the current session and clears the cookie."""
    req_res = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )
    cookies = login_res.cookies

    logout_res = client.post("/api/v1/sessions/logout", cookies=cookies)
    assert logout_res.status_code == 200

    session = db_session.query(AuthSession).filter_by(user_id=test_user.id).first()
    assert session.revoked_at is not None
    assert client.post("/api/v1/sessions/refresh", cookies=cookies).status_code == 401


def test_14_logout_all(client: TestClient, test_user: User, db_session):
    """14. Test that logout-all revokes all active sessions for the user."""
    req1 = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    log1 = client.post("/api/v1/admin/auth/otp/verify", json={"identifier": test_user.email, "otp": req1.json()["data"]["dev_otp"]})
    token1 = log1.json()["data"]["access_token"]
    cookies1 = log1.cookies

    req2 = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    log2 = client.post("/api/v1/admin/auth/otp/verify", json={"identifier": test_user.email, "otp": req2.json()["data"]["dev_otp"]})
    cookies2 = log2.cookies

    logout_all_res = client.post("/api/v1/sessions/logout-all", headers={"Authorization": f"Bearer {token1}"})
    assert logout_all_res.status_code == 200

    assert client.post("/api/v1/sessions/refresh", cookies=cookies1).status_code == 401
    assert client.post("/api/v1/sessions/refresh", cookies=cookies2).status_code == 401


def test_15_user_cannot_revoke_another_users_session(
    client: TestClient, test_user: User, second_user: User, db_session
):
    """15. Test that a user cannot revoke another user's session (returns 404)."""
    req_sec = client.post("/api/v1/admin/auth/otp/request", json={"identifier": second_user.email})
    client.post("/api/v1/admin/auth/otp/verify", json={"identifier": second_user.email, "otp": req_sec.json()["data"]["dev_otp"]})
    second_session = db_session.query(AuthSession).filter_by(user_id=second_user.id).first()

    req_first = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    log_first = client.post("/api/v1/admin/auth/otp/verify", json={"identifier": test_user.email, "otp": req_first.json()["data"]["dev_otp"]})
    first_token = log_first.json()["data"]["access_token"]

    del_res = client.delete(
        f"/api/v1/sessions/{second_session.id}",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert del_res.status_code == 404

    db_session.refresh(second_session)
    assert second_session.revoked_at is None


def test_16_refresh_token_reuse_replay_handling(client: TestClient, test_user: User):
    """16. Test that replaying an already-rotated refresh token revokes all user sessions (theft defense)."""
    req = client.post("/api/v1/admin/auth/otp/request", json={"identifier": test_user.email})
    log = client.post("/api/v1/admin/auth/otp/verify", json={"identifier": test_user.email, "otp": req.json()["data"]["dev_otp"]})
    old_cookies = dict(log.cookies)

    ref1 = client.post("/api/v1/sessions/refresh", cookies=old_cookies)
    assert ref1.status_code == 200
    valid_cookies = ref1.cookies

    replay_res = client.post("/api/v1/sessions/refresh", cookies=old_cookies)
    assert replay_res.status_code == 401
    assert "reuse detected" in replay_res.json()["message"]

    assert client.post("/api/v1/sessions/refresh", cookies=valid_cookies).status_code == 401


def test_17_missing_refresh_cookie(client: TestClient):
    """17. Test that refresh endpoint returns 401 if no refresh cookie is sent."""
    assert client.post("/api/v1/sessions/refresh").status_code == 401


def test_18_invalid_refresh_token(client: TestClient):
    """18. Test that an invalid/non-existent refresh token returns 401."""
    res = client.post("/api/v1/sessions/refresh", cookies={settings.REFRESH_COOKIE_NAME: "invalid-token"})
    assert res.status_code == 401


def test_active_session_marks_current_without_refresh_cookie(client: TestClient, test_user: User):
    """The access token identifies the current session when the cookie is unavailable."""
    req_res = client.post(
        "/api/v1/admin/auth/otp/request",
        json={"identifier": test_user.email},
    )
    login_res = client.post(
        "/api/v1/admin/auth/otp/verify",
        json={"identifier": test_user.email, "otp": req_res.json()["data"]["dev_otp"]},
    )

    sessions_res = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {login_res.json()['data']['access_token']}"},
    )

    assert sessions_res.status_code == 200
    sessions = sessions_res.json()["data"]
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True


def test_19_admin_google_login(client: TestClient, test_user: User, db_session, monkeypatch):
    """19. Test Admin Continue with Google."""
    async def fake_upload_google_profile_picture(picture_url: str) -> str:
        assert picture_url.startswith("https://lh3.googleusercontent.com/")
        return "https://res.cloudinary.com/example/image/upload/profile-picture/admin.jpg"

    monkeypatch.setattr(
        "app.services.auth_service.upload_google_profile_picture",
        fake_upload_google_profile_picture,
    )
    google_token = make_mock_google_id_token(
        email=test_user.email,
        name=test_user.name,
        picture="https://lh3.googleusercontent.com/a/new-admin-pic.jpg",
    )
    res = client.post(
        "/api/v1/admin/auth/google",
        json={"id_token": google_token},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "access_token" in data
    db_session.refresh(test_user)
    assert test_user.profile_pic == "https://res.cloudinary.com/example/image/upload/profile-picture/admin.jpg"
    assert settings.REFRESH_COOKIE_NAME in res.cookies


def test_20_customer_google_login_with_profile_pic_and_visitor(client: TestClient, db_session, monkeypatch):
    """20. Test Customer Continue with Google (auto-registration + avatar + visitor linking)."""
    async def fake_upload_google_profile_picture(picture_url: str) -> str:
        assert picture_url.startswith("https://lh3.googleusercontent.com/")
        return "https://res.cloudinary.com/example/image/upload/profile-picture/customer.jpg"

    monkeypatch.setattr(
        "app.services.auth_service.upload_google_profile_picture",
        fake_upload_google_profile_picture,
    )
    visitor = Visitor(visitor_code="VIS-GGL01", lead_score=15)
    db_session.add(visitor)
    db_session.commit()
    db_session.refresh(visitor)

    google_token = make_mock_google_id_token(
        email="sandra.adventurer@gmail.com",
        name="Sandra Adventurer",
        picture="https://lh3.googleusercontent.com/a/sandra-avatar.png",
    )

    res = client.post(
        "/api/v1/enduser/auth/google",
        json={"id_token": google_token, "visitor_id": str(visitor.id)},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "access_token" in data
    assert data["customer"]["name"] == "Sandra Adventurer"
    assert data["customer"]["email"] == "sandra.adventurer@gmail.com"
    assert data["customer"]["profile_pic"] == "https://res.cloudinary.com/example/image/upload/profile-picture/customer.jpg"

    # Assert visitor is linked to new customer
    cust_id = uuid.UUID(data["customer"]["id"])
    db_session.refresh(visitor)
    assert visitor.customer_id == cust_id


def test_21_room_and_vehicle_float_types(db_session):
    """21. Test that Room and Vehicle models use float/Decimal for prices."""
    room = Room(room_code="RM-101", room_number="101", price_per_night=Decimal("2500.50"), is_active=True)
    vehicle = Vehicle(vehicle_code="VH-01", name="Innova Crysta", registration_number="WB-64-1234", capacity=7, price_per_day=Decimal("3200.75"), is_active=True)
    db_session.add(room)
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(room)
    db_session.refresh(vehicle)

    assert float(room.price_per_night) == 2500.50
    assert float(vehicle.price_per_day) == 3200.75
