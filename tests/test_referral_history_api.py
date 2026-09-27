from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_customer
from app.core.enums import AccountRole, BookingSource, BookingStatus, LeadSource, ReferralStatus, TourType
from app.db.database import get_db
from app.main import app
from app.models.account import Account
from app.models.base import Base
from app.models.booking import Booking
from app.models.customer_profile import CustomerProfile
from app.models.referral import Referral
from app.models.referral_reward_history import ReferralRewardHistory


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_customer_referral_history_includes_reward_and_booking_details():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    referrer = Account(
        account_code="CUS-REFERRER-API",
        name="Referrer",
        email="referrer@example.com",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    referred = Account(
        account_code="CUS-REFERRED-API",
        name="Referred Customer",
        email="referred@example.com",
        mobile="+919900001234",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    db.add_all([referrer, referred])
    db.flush()
    db.add_all(
        [
            CustomerProfile(
                account_id=referrer.id,
                source=LeadSource.WEBSITE,
                referral_code="REF-API-TEST",
            ),
            CustomerProfile(
                account_id=referred.id,
                source=LeadSource.WEBSITE,
                referral_code="REF-REFERRED",
            ),
        ]
    )
    db.flush()
    referral = Referral(
        referrer_customer_id=referrer.id,
        referred_customer_id=referred.id,
        status=ReferralStatus.REWARD_CREDITED,
        default_reward_amount=Decimal("500.00"),
        converted_at=datetime(2026, 9, 27, 5, 0, tzinfo=timezone.utc),
    )
    db.add(referral)
    db.flush()
    credit_date = datetime(2026, 9, 27, 5, 2, tzinfo=timezone.utc)
    db.add(
        ReferralRewardHistory(
            referral_id=referral.id,
            approved_reward_amount=Decimal("500.00"),
            credit_date=credit_date,
        )
    )
    booking = Booking(
        booking_code="BK-REF-API",
        customer_id=referred.id,
        booking_type=TourType.DOMESTIC,
        source=BookingSource.APP,
        status=BookingStatus.COMPLETED,
        adult_count=1,
        child_count=0,
        senior_count=0,
        subtotal=Decimal("1000.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("1000.00"),
        paid_amount=Decimal("1000.00"),
        due_amount=Decimal("0.00"),
        created_by=referred.id,
    )
    db.add(booking)
    db.commit()
    db.refresh(referrer)
    db.refresh(referred)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_customer] = lambda: referrer
    try:
        with TestClient(app) as client:
            code_response = client.get("/api/v1/referrals/code")
            assert code_response.status_code == 200
            assert code_response.json()["data"]["referral_code"] == "REF-API-TEST"

            invite_response = client.get("/api/v1/referrals/invite/ref-api-test")
            assert invite_response.status_code == 200
            assert invite_response.json()["data"] == {
                "referral_code": "REF-API-TEST",
                "referrer_name": "Referrer",
            }
            invalid_invite_response = client.get("/api/v1/referrals/invite/missing-code")
            assert invalid_invite_response.status_code == 404
            assert invalid_invite_response.json()["message"] == "Invalid referral code."

            response = client.get("/api/v1/referrals", params={"page": 1, "page_size": 10})
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["message"] == "Items fetched successfully"
    assert body["pagination"]["total_items"] == 1
    item = body["data"][0]
    assert item["referral_code"] == "REF-API-TEST"
    assert item["reward_amount"] == "500.00"
    assert item["transaction_date"].startswith("2026-09-27T05:02:00")
    assert item["currency"] == "INR"
    assert item["payment_method"] == "WALLET"
    referred_data = item["referred_customer"]
    assert {
        key: referred_data[key]
        for key in (
            "id",
            "customer_code",
            "name",
            "email",
            "mobile",
            "booking_id",
            "booking_code",
        )
    } == {
        "id": str(referred.id),
        "customer_code": "CUS-REFERRED-API",
        "name": "Referred Customer",
        "email": "referred@example.com",
        "mobile": "+919900001234",
        "booking_id": str(booking.id),
        "booking_code": "BK-REF-API",
    }
    assert referred_data["booking_date"].startswith("2026-")