from sqlalchemy import inspect

from app.models.customer import Customer
from app.models.referral import Referral


def test_referral_has_referred_customer_fk_and_relationships():
    table = Referral.__table__
    assert "referred_customer_id" in table.columns

    mapper = inspect(Referral)
    assert "referred_customer" in mapper.relationships
    assert "referrer" in mapper.relationships

    customer_mapper = inspect(Customer)
    assert "referrals_made" in customer_mapper.relationships
    assert "referral_received" in customer_mapper.relationships
