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


def test_create_and_manage_vendor_financial_accounts(db_session: Session):
    vendor = Vendor(name="Test Vendor", type="HOTEL")
    db_session.add(vendor)
    db_session.commit()

    service = FinancialAccountService(db_session)

    created = service.create_account(
        FinancialAccountCreate(
            account_code="BANK-1001",
            name="Vendor bank account",
            account_type=FinancialAccountType.CURRENT,
            owner_type=FinancialAccountOwnerType.VENDOR,
            owner_id=vendor.id,
        )
    )

    assert created.owner_id == vendor.id
    assert created.is_active is True

    items, total = service.list_accounts(
        owner_type=FinancialAccountOwnerType.VENDOR,
        account_type=FinancialAccountType.CURRENT,
        page=1,
        page_size=20,
    )
    assert total == 1
    assert items[0].id == created.id

    updated = service.update_account(
        created.id,
        FinancialAccountUpdate(name="Updated vendor bank", is_active=False),
    )
    assert updated.name == "Updated vendor bank"
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


def test_customer_financial_accounts_are_not_supported(db_session: Session):
    customer = Account(
        account_code="CUS-1002",
        name="Customer without bank",
        email="customer2@example.com",
        mobile="8888888888",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    db_session.add(customer)
    db_session.commit()

    service = FinancialAccountService(db_session)
    with pytest.raises(ValueError, match="customer.*bank|customer.*not supported|not supported"):
        service.create_account(
            FinancialAccountCreate(
                account_code="BANK-CUS-1002",
                name="Customer bank",
                account_type=FinancialAccountType.CURRENT,
                owner_type=FinancialAccountOwnerType.CUSTOMER,
                owner_id=customer.id,
            )
        )
