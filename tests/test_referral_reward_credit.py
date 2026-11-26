from datetime import datetime, timedelta
from decimal import Decimal
import uuid

import app.models
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.enums import (
    AccountRole,
    BookingSource,
    BookingStatus,
    FinancialTransactionCategory,
    ReferralStatus,
    TourType,
)
from app.models.account import Account
from app.models.base import Base
from app.models.booking import Booking
from app.models.financial_transaction import FinancialTransaction
from app.models.referral import Referral
from app.models.referral_reward_history import ReferralRewardHistory
from app.schemas.referral import ReferralManualUpdateRequest
from app.services.booking_service import BookingService
from app.services.financial_transaction_service import FinancialTransactionService
from app.services.referral_service import ReferralService
from app.services.wallet_service import WalletService


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_referral_booking(
    db: Session,
    *,
    referral_status: ReferralStatus,
    booking_completed_at: datetime | None = None,
) -> tuple[Account, Account, Account, Referral, Booking]:
    referrer = Account(
        account_code=f"CUS-REF-{uuid.uuid4().hex[:8]}",
        name="Referrer",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    referred = Account(
        account_code=f"CUS-REFERRED-{uuid.uuid4().hex[:8]}",
        name="Referred",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    admin = Account(
        account_code=f"ADMIN-{uuid.uuid4().hex[:8]}",
        name="Admin",
        role=AccountRole.ADMIN,
        is_active=True,
    )
    db.add_all([referrer, referred, admin])
    db.flush()

    referral = Referral(
        referrer_customer_id=referrer.id,
        referred_customer_id=referred.id,
        status=referral_status,
        default_reward_amount=Decimal("500.00"),
        booking_window_days=30,
        booking_completed_at=booking_completed_at,
    )
    booking = Booking(
        booking_code=f"BK-{uuid.uuid4().hex[:8]}",
        customer_id=referred.id,
        booking_type=TourType.DOMESTIC,
        source=BookingSource.WEBSITE,
        status=BookingStatus.CONFIRMED,
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
    db.add_all([referral, booking])
    db.commit()
    return referrer, referred, admin, referral, booking


def test_scheduler_credits_approved_referral_once(db: Session):
    referrer, _, admin, referral, booking = create_referral_booking(
        db,
        referral_status=ReferralStatus.REGISTERED,
    )
    db.add(
        ReferralRewardHistory(
            referral_id=referral.id,
            approved_reward_amount=Decimal("750.00"),
        )
    )
    db.commit()

    service = BookingService(db)
    service.update_booking_status(booking.id, BookingStatus.COMPLETED)
    service.update_booking_status(booking.id, BookingStatus.COMPLETED)

    assert WalletService(db).get_wallet_balance(referrer.id).balance == Decimal("0.00")
    referral_service = ReferralService(db)
    assert referral_service.process_eligible_rewards() == {
        "credited": 0,
        "skipped": 1,
        "failed": 0,
    }
    db.refresh(referral)
    assert referral.status == ReferralStatus.REWARD_ELIGIBLE
    assert WalletService(db).get_wallet_balance(referrer.id).balance == Decimal("0.00")

    ReferralService(db).update_referral(
        referral_id=referral.id,
        payload=ReferralManualUpdateRequest(status=ReferralStatus.REWARD_APPROVED),
        current_user=admin,
    )

    db.refresh(referral)
    assert referral.status == ReferralStatus.REWARD_CREDITED
    assert WalletService(db).get_wallet_balance(referrer.id).balance == Decimal("750.00")
    assert referral_service.process_eligible_rewards() == {
        "credited": 0,
        "skipped": 0,
        "failed": 0,
    }

    db.refresh(referral)
    assert referral.status == ReferralStatus.REWARD_CREDITED
    assert referral.reward_history[0].credit_date is not None
    assert WalletService(db).get_wallet_balance(referrer.id).balance == Decimal("750.00")
    assert db.scalar(
        select(func.count(FinancialTransaction.id)).where(
            FinancialTransaction.external_reference == f"referral-reward:{referral.id}",
            FinancialTransaction.category == FinancialTransactionCategory.REFERRAL_REWARD,
        )
    ) == 1
    report = FinancialTransactionService(db).build_report("referral_income")
    assert report["totals"]["referral_income"] == Decimal("750.00")
    assert report["rows"][0]["category"] == FinancialTransactionCategory.REFERRAL_REWARD.value


def test_scheduler_skips_booking_outside_referral_window(db: Session):
    referrer, _, _, referral, booking = create_referral_booking(
        db,
        referral_status=ReferralStatus.REWARD_APPROVED,
    )
    referral.created_at = referral.created_at - timedelta(days=31)
    booking.created_at = referral.created_at + timedelta(days=30, seconds=1)
    db.commit()
    BookingService(db).update_booking_status(booking.id, BookingStatus.COMPLETED)

    summary = ReferralService(db).process_eligible_rewards()

    assert summary == {"credited": 0, "skipped": 1, "failed": 0}
    assert WalletService(db).get_wallet_balance(referrer.id).balance == Decimal("0.00")


def test_admin_cannot_force_credit_without_eligibility(db: Session):
    referrer, _, admin, referral, _ = create_referral_booking(
        db,
        referral_status=ReferralStatus.REGISTERED,
    )

    with pytest.raises(HTTPException) as exc_info:
        ReferralService(db).update_referral(
            referral_id=referral.id,
            payload=ReferralManualUpdateRequest(status=ReferralStatus.REWARD_CREDITED),
            current_user=admin,
        )

    assert exc_info.value.status_code == 400
    assert WalletService(db).get_wallet_balance(referrer.id).balance == Decimal("0.00")


def test_scheduler_credits_referral_approved_after_booking_completion(db: Session):
    referrer, _, admin, referral, booking = create_referral_booking(
        db,
        referral_status=ReferralStatus.REGISTERED,
    )
    BookingService(db).update_booking_status(booking.id, BookingStatus.COMPLETED)
    db.refresh(referral)
    assert referral.status == ReferralStatus.REGISTERED

    ReferralService(db).update_referral(
        referral_id=referral.id,
        payload=ReferralManualUpdateRequest(status=ReferralStatus.REWARD_APPROVED),
        current_user=admin,
    )

    db.refresh(referral)
    assert referral.status == ReferralStatus.REWARD_CREDITED
    assert referral.reward_history[0].approved_reward_amount == Decimal("500.00")
    assert referral.reward_history[0].approved_by_account_id == admin.id
    db.refresh(referral)
    assert referral.status == ReferralStatus.REWARD_CREDITED
    assert referral.reward_history[0].credit_date is not None
    assert WalletService(db).get_wallet_balance(referrer.id).balance == Decimal("500.00")
    assert ReferralService(db).process_eligible_rewards() == {
        "credited": 0,
        "skipped": 0,
        "failed": 0,
    }
