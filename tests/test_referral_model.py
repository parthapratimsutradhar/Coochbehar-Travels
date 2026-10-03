from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.enums import AccountRole, LeadSource
from app.models.account import Account
from app.models.base import Base
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
