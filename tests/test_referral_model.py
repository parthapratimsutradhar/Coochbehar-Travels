from sqlalchemy import inspect

from app.models.account import Account
from app.models.referral import Referral


def test_referral_has_referred_customer_fk_and_relationships():
    table = Referral.__table__
    assert "referred_customer_id" in table.columns

    mapper = inspect(Referral)
    assert "referred_customer" in mapper.relationships
    assert "referrer" in mapper.relationships

    account_mapper = inspect(Account)
    assert "referrals_made" in account_mapper.relationships
    assert "referral_received" in account_mapper.relationships
