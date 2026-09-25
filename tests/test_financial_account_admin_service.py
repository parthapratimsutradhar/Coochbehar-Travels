import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import AccountRole, FinancialAccountOwnerType, FinancialAccountType
from app.models.account import Account
from app.models.base import Base
from app.models.financial_account import FinancialAccount
from app.models.vendor import Vendor
from app.schemas.financial import FinancialAccountCreate, FinancialAccountUpdate
from app.services.financial_account_service import FinancialAccountService


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_and_manage_customer_financial_accounts(db_session: Session):
    customer = Account(
        account_code="CUS-1001",
        name="Test Customer",
        email="customer@example.com",
        mobile="9999999999",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    vendor = Vendor(name="Test Vendor", type="HOTEL")
    db_session.add_all([customer, vendor])
    db_session.commit()

    service = FinancialAccountService(db_session)

    created = service.create_account(
        FinancialAccountCreate(
            account_code="WALLET-1001",
            name="Customer wallet",
            account_type=FinancialAccountType.CASH,
            owner_type=FinancialAccountOwnerType.CUSTOMER,
            owner_id=customer.id,
        )
    )

    assert created.owner_id == customer.id
    assert created.is_active is True

    items, total = service.list_accounts(
        owner_type=FinancialAccountOwnerType.CUSTOMER,
        account_type=FinancialAccountType.CASH,
        page=1,
        page_size=20,
    )
    assert total == 1
    assert items[0].id == created.id

    updated = service.update_account(
        created.id,
        FinancialAccountUpdate(name="Updated wallet", is_active=False),
    )
    assert updated.name == "Updated wallet"
    assert updated.is_active is False

    service.delete_account(created.id)
    assert service.get_account(created.id).is_active is False


def test_create_customer_account_requires_valid_owner(db_session: Session):
    service = FinancialAccountService(db_session)
    with pytest.raises(ValueError):
        service.create_account(
            FinancialAccountCreate(
                account_code="INVALID-OWNER",
                name="Bad Owner",
                account_type=FinancialAccountType.CURRENT,
                owner_type=FinancialAccountOwnerType.CUSTOMER,
                owner_id=uuid.uuid4(),
            )
        )
