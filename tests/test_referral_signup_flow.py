import uuid
from decimal import Decimal
from unittest.mock import patch
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import AccountRole, LeadSource, ReferralStatus
from app.core.messages.error import ReferralError
from app.db.database import get_db
from app.main import app
from app.models.account import Account
from app.models.base import Base
from app.models.customer_profile import CustomerProfile
from app.models.referral import Referral
from app.models.referral_config import ReferralRewardConfig
from app.repository.customer_repo import CustomerRepository

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
    db = TestingSessionLocal()
    config = ReferralRewardConfig(
        default_reward_amount=Decimal("750.00"),
        booking_window_days=45,
    )
    db.add(config)
    db.commit()

    customer_repo = CustomerRepository(db)
    customer_repo.create_customer(
        name="Alice Referrer",
        email="alice@example.com",
        mobile="+919876543210",
        referral_code="ALICE100",
    )
    db.close()
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
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_validate_referral_invite_success(client):
    resp = client.get("/api/v1/referrals/invite/ALICE100")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["referral_code"] == "ALICE100"
    assert data["referrer_name"] == "Alice Referrer"


def test_validate_referral_invite_rejects_invalid_code(client):
    resp = client.get("/api/v1/referrals/invite/NONEXISTENT")
    assert resp.status_code == 404
    assert resp.json()["message"] == ReferralError.INVALID_CODE


def test_validate_referral_invite_rejects_existing_account(client):
    resp = client.get("/api/v1/referrals/invite/ALICE100?identifier=alice@example.com")
    assert resp.status_code == 400
    assert resp.json()["message"] in (ReferralError.EXISTING_ACCOUNT, ReferralError.SELF_REFERRAL)


def test_validate_referral_invite_accepts_new_identifier(client):
    resp = client.get("/api/v1/referrals/invite/ALICE100?identifier=bob@example.com")
    assert resp.status_code == 200
    assert resp.json()["data"]["referral_code"] == "ALICE100"


def test_request_otp_rejects_existing_account_with_referral(client):
    resp = client.post(
        "/api/v1/auth/otp/request",
        json={
            "identifier": "alice@example.com",
            "purpose": "SIGNUP",
            "referral_code": "ALICE100",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["message"] in (ReferralError.EXISTING_ACCOUNT, ReferralError.SELF_REFERRAL)


def test_signup_otp_flow_creates_referral_using_latest_models(client, db_session):
    # 1. Request OTP for brand new user Bob
    req_resp = client.post(
        "/api/v1/auth/otp/request",
        json={
            "identifier": "bob@example.com",
            "purpose": "SIGNUP",
            "referral_code": "ALICE100",
        },
    )
    assert req_resp.status_code == 200
    dev_otp = req_resp.json()["data"]["dev_otp"]
    assert dev_otp is not None

    # 2. Verify OTP with referral_code
    verify_resp = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "identifier": "bob@example.com",
            "otp": dev_otp,
            "name": "Bob Referred",
            "purpose": "SIGNUP",
            "referral_code": "ALICE100",
        },
    )
    assert verify_resp.status_code == 200
    token_data = verify_resp.json()["data"]
    assert "access_token" in token_data

    # 3. Verify that Referral record was properly created with latest model fields
    referral = db_session.query(Referral).first()
    assert referral is not None
    assert referral.status == ReferralStatus.REGISTERED
    assert referral.default_reward_amount == Decimal("750.00")
    assert referral.booking_window_days == 45
    assert referral.referrer.name == "Alice Referrer"
    assert referral.referred_customer.name == "Bob Referred"


def test_signup_otp_rejects_already_existing_account_on_verify(client):
    req_resp = client.post(
        "/api/v1/auth/otp/request",
        json={
            "identifier": "alice@example.com",
            "purpose": "LOGIN",
        },
    )
    assert req_resp.status_code == 200
    dev_otp = req_resp.json()["data"]["dev_otp"]

    verify_resp = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "identifier": "alice@example.com",
            "otp": dev_otp,
            "purpose": "LOGIN",
            "referral_code": "ALICE100",
        },
    )
    assert verify_resp.status_code == 400
    assert verify_resp.json()["message"] == ReferralError.EXISTING_ACCOUNT


def test_google_login_creates_referral_for_new_customer(client, db_session):
    fake_payload = {
        "email": "charlie@example.com",
        "name": "Charlie Google",
        "picture": "https://example.com/pic.png",
    }
    with patch("app.services.auth_service.verify_google_id_token", return_value=fake_payload), \
         patch("app.services.auth_service.upload_google_profile_picture", return_value="https://cdn.example.com/charlie.png"):
        resp = client.post(
            "/api/v1/auth/google",
            json={
                "id_token": "valid-token-for-charlie",
                "referral_code": "ALICE100",
            },
        )
        assert resp.status_code == 200

    referral = db_session.query(Referral).join(Account, Referral.referred_customer_id == Account.id).filter(Account.email == "charlie@example.com").first()
    assert referral is not None
    assert referral.default_reward_amount == Decimal("750.00")
    assert referral.booking_window_days == 45
    assert referral.referred_customer.name == "Charlie Google"


def test_google_login_rejects_referral_code_for_existing_customer(client):
    fake_payload = {
        "email": "david@example.com",
        "name": "David Google",
    }
    with patch("app.services.auth_service.verify_google_id_token", return_value=fake_payload):
        resp1 = client.post(
            "/api/v1/auth/google",
            json={"id_token": "valid-token-for-david"},
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            "/api/v1/auth/google",
            json={
                "id_token": "valid-token-for-david",
                "referral_code": "ALICE100",
            },
        )
        assert resp2.status_code == 400
        assert resp2.json()["message"] == ReferralError.EXISTING_ACCOUNT
