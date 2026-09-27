import json
import sqlite3
from decimal import Decimal

import pytest
from sqlalchemy import ARRAY, create_engine
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.api.deps import get_current_customer
from app.core.enums import (
    AccountRole,
    FinancialTransactionCategory,
    FinancialTransactionStatus,
    FinancialTransactionType,
    PaymentMethod,
    PaymentStatus,
)
from app.db.database import get_db
from app.main import app
from app.models.account import Account
from app.models.base import Base
from app.models.financial_transaction import FinancialTransaction
from app.models.vendor import Vendor
from app.repository.customer_repo import CustomerRepository
from app.services.financial_reporting_service import FinancialReportingService
from app.services.financial_service import FinancialService
from app.services.wallet_service import WalletService


compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")
compiles(ARRAY, "sqlite")(lambda type_, compiler, **kw: "JSON")
compiles(PG_ARRAY, "sqlite")(lambda type_, compiler, **kw: "JSON")
sqlite3.register_adapter(list, lambda value: json.dumps([str(item) for item in value]))

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def database():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_wallet_top_up_is_idempotent_and_failed_payment_does_not_credit():
    with SessionLocal() as db:
        customer = CustomerRepository(db).create_customer(name="Wallet Customer", mobile="+919000000001")
        service = WalletService(db)
        failed = service.record_top_up(
            customer_id=customer.id,
            amount=Decimal("10"),
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.FAILED,
            gateway="test",
            gateway_transaction_id=None,
            external_reference="failed-1",
            description="declined",
        )
        credited = service.record_top_up(
            customer_id=customer.id,
            amount=Decimal("100"),
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.SUCCESS,
            gateway="test",
            gateway_transaction_id="gateway-1",
            external_reference="topup-1",
            description="verified",
        )
        duplicate = service.record_top_up(
            customer_id=customer.id,
            amount=Decimal("100"),
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.SUCCESS,
            gateway="test",
            gateway_transaction_id="gateway-1",
            external_reference="topup-1",
            description="duplicate",
        )
        wallet = service.get_wallet_account(customer.id)
        assert failed.status.value == "FAILED"
        assert duplicate.id == credited.id
        assert service.balance(wallet) == Decimal("100.00")


def test_customer_wallet_balance_api_sums_completed_ledger_entries():
    with SessionLocal() as db:
        customer = CustomerRepository(db).create_customer(
            name="Wallet API Customer",
            mobile="+919000000002",
        )
        admin = Account(
            account_code="ADMIN-WALLET-API",
            name="Wallet API Admin",
            role=AccountRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        service = WalletService(db)
        service.record_top_up(
            customer_id=customer.id,
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.SUCCESS,
            gateway="test",
            gateway_transaction_id="wallet-api-credit",
            external_reference="wallet-api-credit",
            description="completed credit",
        )
        service.adjust(
            customer_id=customer.id,
            amount=Decimal("30.00"),
            direction="DEBIT",
            reason="completed debit",
            actor=admin,
            reference="wallet-api-debit",
        )
        service.record_top_up(
            customer_id=customer.id,
            amount=Decimal("50.00"),
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.PENDING,
            gateway="test",
            gateway_transaction_id=None,
            external_reference="wallet-api-pending",
            description="pending credit",
        )
        db.add(
            FinancialTransaction(
                transaction_code="FT-CUSTOMER-VENDOR-PAYMENT",
                transaction_type=FinancialTransactionType.EXPENSE,
                status=FinancialTransactionStatus.COMPLETED,
                amount=Decimal("20.00"),
                currency="INR",
                category=FinancialTransactionCategory.VENDOR_PAYMENT,
                customer_id=customer.id,
                description="vendor payment should not appear in customer history",
            )
        )
        db.commit()
        other_customer = CustomerRepository(db).create_customer(
            name="Another Wallet Customer",
            mobile="+919000000003",
        )
        service.record_top_up(
            customer_id=other_customer.id,
            amount=Decimal("15.00"),
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.SUCCESS,
            gateway="test",
            gateway_transaction_id="wallet-api-other-customer",
            external_reference="wallet-api-other-customer",
            description="other customer's credit",
        )

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_customer] = lambda: customer
        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/transactions/balance")
                transactions_response = client.get(
                    "/api/v1/transactions",
                    params={"page": 1, "page_size": 10},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()["data"]
        assert Decimal(data["balance"]) == Decimal("70.00")
        assert data["customer_id"] == str(customer.id)
        assert data["currency"] == "INR"
        assert transactions_response.status_code == 200
        transactions_body = transactions_response.json()
        assert transactions_body["pagination"]["total_items"] == 3
        assert all(
            item["category"] != "vendor_payment"
            for item in transactions_body["data"]
        )
        assert all(
            item["customer_id"] == str(customer.id)
            for item in transactions_body["data"]
        )
        assert all("booking_code" in item and "created_by" in item for item in transactions_body["data"])
        debit_transaction = next(
            item
            for item in transactions_body["data"]
            if item["description"] == "completed debit"
        )
        assert debit_transaction["booking_code"] is None
        assert debit_transaction["created_by"] == {
            "account_id": str(admin.id),
            "name": admin.name,
            "email": admin.email,
            "mobile": admin.mobile,
            "profile_picture": admin.profile_pic,
        }


def test_customer_transactions_endpoint_filters_by_category_and_status():
    with SessionLocal() as db:
        customer = CustomerRepository(db).create_customer(name="Filtered Customer", mobile="+919000000004")
        admin = Account(account_code="ADMIN-FILTER-TEST", name="Filter Admin", role=AccountRole.ADMIN, is_active=True)
        db.add(admin)
        db.commit()

        WalletService(db).record_top_up(
            customer_id=customer.id,
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.SUCCESS,
            gateway="test",
            gateway_transaction_id="filter-topup-success",
            external_reference="filter-topup-success",
            description="successful top-up",
        )
        WalletService(db).record_top_up(
            customer_id=customer.id,
            amount=Decimal("50.00"),
            payment_method=PaymentMethod.RAZORPAY,
            payment_status=PaymentStatus.PENDING,
            gateway="test",
            gateway_transaction_id=None,
            external_reference="filter-topup-pending",
            description="pending top-up",
        )

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_customer] = lambda: customer
        try:
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/transactions",
                    params={"page": 1, "page_size": 10, "category": "WALLET_CREDIT", "status": "COMPLETED"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total_items"] == 1
        assert body["data"][0]["category"] == "wallet_credit"
        assert body["data"][0]["status"] == "COMPLETED"


def test_vendor_payment_reversal_is_audited_and_reported_as_history():
    with SessionLocal() as db:
        admin = Account(account_code="ADMIN-FIN-TEST", name="Finance Admin", role=AccountRole.ADMIN, is_active=True)
        vendor = Vendor(vendor_code="VEN-FIN-TEST", name="Finance Vendor", type="HOTEL")
        db.add_all([admin, vendor])
        db.commit()
        service = FinancialService(db)
        payment = service.record_vendor_payment(
            amount=Decimal("50"),
            vendor_id=vendor.id,
            booking_id=None,
            cost_id=None,
            currency="INR",
            payment_method=PaymentMethod.CASH,
            reference="vendor-payment-1",
            description="settlement",
            recorded_by_account_id=admin.id,
            transaction_date=None,
        )
        service.reverse_transaction(transaction_id=payment.id, actor_id=admin.id, reason="duplicate")
        report = FinancialReportingService(db).report("vendor-payments")
        assert report.rows[0]["status"] == "REVERSED"
        assert report.totals["amount"] == Decimal("0")
