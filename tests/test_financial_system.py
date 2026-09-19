import json
import sqlite3
from decimal import Decimal

import pytest
from sqlalchemy import ARRAY, create_engine
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import AccountRole, PaymentMethod, PaymentStatus
from app.models.account import Account
from app.models.base import Base
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
