from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.enums import (
    AccountRole,
    BookingSource,
    BookingStatus,
    LeadSource,
    ReferralStatus,
    TourType,
)
from app.models.account import Account
from app.models.base import Base
from app.models.booking import Booking
from app.models.customer_profile import CustomerProfile
from app.models.referral import Referral
from app.services.referral_service import ReferralService


def test_referral_has_referred_customer_fk_and_relationships():
    table = Referral.__table__
    assert "referred_customer_id" in table.columns

    mapper = inspect(Referral)
    assert "referred_customer" in mapper.relationships
    assert "referrer" in mapper.relationships

    account_mapper = inspect(Account)
    assert "referrals_made" in account_mapper.relationships
    assert "referral_received" in account_mapper.relationships


def test_referral_code_is_created_for_customer_without_profile():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            customer = Account(
                account_code="CUS-NO-PROFILE",
                name="Legacy Customer",
                email="legacy-customer@example.com",
                role=AccountRole.CUSTOMER,
                is_active=True,
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)

            response = ReferralService(db).get_customer_referral_code(customer.id)

            profile = db.query(CustomerProfile).filter_by(account_id=customer.id).one()
            assert len(response.referral_code) == 8
            assert response.referral_code.isalnum()
            assert response.referral_code == response.referral_code.upper()
            assert profile.referral_code == response.referral_code
            assert profile.source == LeadSource.WEBSITE
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_referral_list_includes_referral_acceptance_and_first_booking_times():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sent_at = datetime(2026, 9, 1, 10, 0)
    accepted_at = datetime(2026, 9, 2, 11, 0)
    first_booking_at = datetime(2026, 9, 3, 12, 0)
    second_booking_at = datetime(2026, 9, 4, 13, 0)
    try:
        with Session(engine) as db:
            referrer = Account(
                account_code="CUS-REF-TIME",
                name="Referrer",
                role=AccountRole.CUSTOMER,
                is_active=True,
                created_at=sent_at,
            )
            referred = Account(
                account_code="CUS-REFERRED-TIME",
                name="Referred",
                role=AccountRole.CUSTOMER,
                is_active=True,
                created_at=accepted_at,
            )
            db.add_all([referrer, referred])
            db.flush()
            referral = Referral(
                referrer_customer_id=referrer.id,
                referred_customer_id=referred.id,
                status=ReferralStatus.REGISTERED,
                default_reward_amount=Decimal("500.00"),
                created_at=sent_at,
            )
            bookings = [
                Booking(
                    booking_code="BK-REF-TIME-1",
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
                    created_at=second_booking_at,
                ),
                Booking(
                    booking_code="BK-REF-TIME-2",
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
                    created_at=first_booking_at,
                ),
            ]
            db.add_all([referral, *bookings])
            db.commit()

            items, total_items = ReferralService(db).list_referrals(
                page=1,
                page_size=10,
                status=None,
                search=None,
            )

            assert total_items == 1
            assert items[0].referral_sent_at == sent_at
            assert items[0].referral_accepted_at == accepted_at
            assert items[0].booking_created_at == first_booking_at
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
