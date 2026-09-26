from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import (
    AccountRole,
    FinancialAccountOwnerType,
    FinancialAccountType,
    FinancialTransactionCategory,
    FinancialTransactionStatus,
    FinancialTransactionType,
)
from app.models.account import Account
from app.models.base import Base
from app.models.financial_account import FinancialAccount
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction_entry import FinancialTransactionEntry
from app.services.customer_service import CustomerService


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_customer_ledger_lists_transactions_and_calculates_wallet_balance(db_session: Session):
    customer = Account(
        account_code="CUS-LEDGER-01",
        name="Ledger Customer",
        email="ledger-customer@example.com",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    db_session.add(customer)
    db_session.flush()
    wallet = FinancialAccount(
        account_code="WALLET-LEDGER-01",
        name="Ledger Customer Wallet",
        account_type=FinancialAccountType.LIABILITY,
        owner_type=FinancialAccountOwnerType.CUSTOMER,
        owner_id=customer.id,
        currency="INR",
        is_active=True,
    )
    db_session.add(wallet)
    db_session.flush()

    transactions = [
        FinancialTransaction(
            transaction_code="FT-LEDGER-CREDIT",
            transaction_type=FinancialTransactionType.INCOME,
            status=FinancialTransactionStatus.COMPLETED,
            customer_id=customer.id,
            amount=Decimal("100.00"),
            currency="INR",
            category=FinancialTransactionCategory.WALLET_CREDIT,
            transaction_date=datetime(2026, 1, 1),
        ),
        FinancialTransaction(
            transaction_code="FT-LEDGER-DEBIT",
            transaction_type=FinancialTransactionType.EXPENSE,
            status=FinancialTransactionStatus.COMPLETED,
            customer_id=customer.id,
            amount=Decimal("30.00"),
            currency="INR",
            category=FinancialTransactionCategory.WALLET_DEBIT,
            transaction_date=datetime(2026, 1, 2),
        ),
        FinancialTransaction(
            transaction_code="FT-LEDGER-BOOKING",
            transaction_type=FinancialTransactionType.INCOME,
            status=FinancialTransactionStatus.COMPLETED,
            customer_id=customer.id,
            amount=Decimal("200.00"),
            currency="INR",
            category=FinancialTransactionCategory.BOOKING_PAYMENT,
            transaction_date=datetime(2026, 1, 3),
        ),
        FinancialTransaction(
            transaction_code="FT-LEDGER-PENDING",
            transaction_type=FinancialTransactionType.INCOME,
            status=FinancialTransactionStatus.PENDING,
            customer_id=customer.id,
            amount=Decimal("25.00"),
            currency="INR",
            category=FinancialTransactionCategory.WALLET_CREDIT,
            transaction_date=datetime(2026, 1, 4),
        ),
    ]
    db_session.add_all(transactions)
    db_session.flush()
    db_session.add_all(
        [
            FinancialTransactionEntry(
                transaction_id=transactions[0].id,
                account_id=wallet.id,
                debit=Decimal("0.00"),
                credit=Decimal("100.00"),
            ),
            FinancialTransactionEntry(
                transaction_id=transactions[1].id,
                account_id=wallet.id,
                debit=Decimal("30.00"),
                credit=Decimal("0.00"),
            ),
        ]
    )
    db_session.commit()

    payload = CustomerService(db_session).get_customer_tab_data(
        customer_id=customer.id,
        customer=customer,
        tab="ledger",
        page=1,
        page_size=10,
    )

    assert payload["tab"] == "ledger"
    assert payload["balance"] == "70.00"
    assert payload["currency"] == "INR"
    assert payload["pagination"]["total_items"] == 4
    assert {item["transaction_code"] for item in payload["items"]} == {
        "FT-LEDGER-CREDIT",
        "FT-LEDGER-DEBIT",
        "FT-LEDGER-BOOKING",
        "FT-LEDGER-PENDING",
    }