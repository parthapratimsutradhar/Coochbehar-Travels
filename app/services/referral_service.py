import logging
import uuid
import secrets
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import (
    AccountRole,
    BookingStatus,
    FinancialTransactionStatus,
    LeadSource,
    PaymentMethod,
    ReferralStatus,
)
from app.core.messages.error import ReferralError
from app.models.account import Account
from app.models.booking import Booking
from app.models.customer_profile import CustomerProfile
from app.models.financial_transaction import FinancialTransaction
from app.models.referral import Referral
from app.models.referral_reward_history import ReferralRewardHistory
from app.repository.customer_repo import CustomerRepository
from app.repository.referral_repo import ReferralRepository
from app.schemas.notification import NotificationCreate
from app.schemas.referral import (
    ReferralHistoryItemResponse,
    ReferralCodeResponse,
    ReferralInviteResponse,
    ReferralListItemResponse,
    ReferralManualUpdateRequest,
    ReferralRewardConfigRequest,
    ReferralRewardConfigResponse,
    ReferredCustomerResponse,
)
from app.services.notification_service import NotificationService
from app.services.wallet_service import WalletService

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReferralRepository(db)

    def validate_invite(
        self,
        referral_code: str,
        identifier: str | None = None,
    ) -> ReferralInviteResponse:
        normalized_code = referral_code.strip().upper()
        referrer_profile = self.repo.get_profile_by_code(normalized_code)
        if (
            referrer_profile is None
            or referrer_profile.account is None
            or not referrer_profile.account.is_active
            or referrer_profile.account.role != AccountRole.CUSTOMER
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ReferralError.INVALID_CODE,
            )

        if identifier:
            customer_repo = CustomerRepository(self.db)
            cleaned = identifier.strip()
            if (
                customer_repo.get_by_identifier(cleaned)
                or customer_repo.has_active_account_with_identifier(cleaned)
                or customer_repo.has_active_customer_with_identifier(cleaned)
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ReferralError.EXISTING_ACCOUNT,
                )
            referrer = referrer_profile.account
            if (
                (referrer.email and referrer.email.strip().lower() == cleaned.lower())
                or (referrer.mobile and referrer.mobile.strip() == cleaned)
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ReferralError.SELF_REFERRAL,
                )

        return ReferralInviteResponse(
            referral_code=referrer_profile.referral_code,
            referrer_name=referrer_profile.account.name,
        )

    def create_referral(
        self,
        referrer: Account,
        referred: Account,
        notes: str = "Created from referral registration.",
    ) -> Referral:
        """Create and persist a referral relationship, using the latest reward configuration."""
        if referrer.id == referred.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ReferralError.SELF_REFERRAL,
            )

        existing = (
            self.db.query(Referral)
            .filter(Referral.referred_customer_id == referred.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ReferralError.EXISTING_ACCOUNT,
            )

        config = self.repo.get_latest_config()
        default_reward = (
            Decimal(str(config.default_reward_amount))
            if config and config.default_reward_amount is not None
            else Decimal("500.00")
        )
        booking_window_days = (
            int(config.booking_window_days)
            if config and config.booking_window_days is not None
            else 30
        )

        referral = Referral(
            referrer_customer_id=referrer.id,
            referred_customer_id=referred.id,
            status=ReferralStatus.REGISTERED,
            default_reward_amount=default_reward,
            booking_window_days=booking_window_days,
            notes=notes,
        )
        self.db.add(referral)
        self.db.commit()
        self.db.refresh(referral)

        try:
            NotificationService(self.db).create(
                NotificationCreate(
                    notification_type="REFERRAL_CREATED",
                    title="Thank you for your referral",
                    message=(
                        f"Thank you for referring {referred.name}. "
                        "Your referral reward will be updated when applicable."
                    ),
                    data={
                        "referred_customer_id": str(referred.id),
                        "referred_customer_name": referred.name,
                        "referral_id": str(referral.id),
                    },
                ),
                customer_id=referrer.id,
            )
        except Exception:
            pass

        return referral

    def get_customer_referral_code(self, customer_id: uuid.UUID) -> ReferralCodeResponse:
        profile = self.repo.get_profile_by_account_id(customer_id)
        if profile:
            return ReferralCodeResponse(referral_code=profile.referral_code)

        customer = self.db.get(Account, customer_id)
        if customer is None or customer.role != AccountRole.CUSTOMER:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

        alphabet = string.ascii_uppercase + string.digits
        for _ in range(5):
            referral_code = "".join(secrets.choice(alphabet) for _ in range(8))
            if self.repo.get_profile_by_code(referral_code):
                continue

            profile = CustomerProfile(
                account_id=customer_id,
                source=LeadSource.WEBSITE,
                referral_code=referral_code,
            )
            self.db.add(profile)
            try:
                self.db.commit()
                self.db.refresh(profile)
                return ReferralCodeResponse(referral_code=profile.referral_code)
            except IntegrityError:
                self.db.rollback()
                profile = self.repo.get_profile_by_account_id(customer_id)
                if profile:
                    return ReferralCodeResponse(referral_code=profile.referral_code)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create a unique referral code. Please try again.",
        )

    @staticmethod
    def _latest_reward_history(referral: Referral) -> ReferralRewardHistory | None:
        return max(referral.reward_history, key=lambda history: history.created_at, default=None)

    @classmethod
    def build_customer_history_item(cls, referral: Referral) -> ReferralHistoryItemResponse:
        referred = referral.referred_customer
        latest_history = cls._latest_reward_history(referral)
        latest_booking = (
            max(referred.bookings, key=lambda booking: booking.created_at)
            if referred and referred.bookings
            else None
        )
        return ReferralHistoryItemResponse(
            id=referral.id,
            referral_code=(
                referral.referrer.customer_profile.referral_code
                if referral.referrer and referral.referrer.customer_profile
                else ""
            ),
            reward_amount=(
                latest_history.approved_reward_amount
                if latest_history
                else referral.default_reward_amount
            ),
            transaction_date=(
                latest_history.credit_date or latest_history.created_at
                if latest_history
                else referral.converted_at
            ),
            currency="INR",
            payment_method=PaymentMethod.WALLET,
            status=referral.status,
            converted_at=referral.converted_at,
            created_at=referral.created_at,
            referred_customer=ReferredCustomerResponse(
                id=referred.id,
                customer_code=referred.account_code,
                name=referred.name,
                email=referred.email,
                mobile=referred.mobile,
                booking_id=latest_booking.id if latest_booking else None,
                booking_code=latest_booking.booking_code if latest_booking else None,
                booking_date=latest_booking.created_at if latest_booking else None,
            ),
        )

    def list_customer_history(
        self,
        referrer_customer_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[ReferralHistoryItemResponse], int]:
        referrals, total_items = self.repo.list_customer_history(
            referrer_customer_id,
            page,
            page_size,
        )
        return [self.build_customer_history_item(referral) for referral in referrals], total_items

    def _referral_to_list_item(self, referral: Referral) -> ReferralListItemResponse:
        referrer = referral.referrer
        referred = referral.referred_customer
        referrer_profile = referrer.customer_profile if referrer and hasattr(referrer, "customer_profile") else None
        first_booking = (
            min(referred.bookings, key=lambda booking: booking.created_at)
            if referred and referred.bookings
            else None
        )
        latest_history = self._latest_reward_history(referral)
        approved_by = latest_history.approved_by if latest_history else None
        return ReferralListItemResponse(
            id=referral.id,
            referral_sent_at=referral.created_at,
            referral_accepted_at=referred.created_at if referred else None,
            booking_created_at=first_booking.created_at if first_booking else None,
            referrer_id=referral.referrer_customer_id,
            referrer_name=referrer.name if referrer else None,
            referrer_profile_image=referrer.profile_pic if referrer else None,
            referrer_code=referrer_profile.referral_code if referrer_profile else None,
            referred_customer_id=referral.referred_customer_id,
            referred_customer_name=referred.name if referred else None,
            referred_customer_profile_image=referred.profile_pic if referred else None,
            referred_customer_code=(referred.account_code if referred else None),
            converted_at=referral.converted_at,
            booking_completed_at=referral.booking_completed_at,
            default_reward_amount=referral.default_reward_amount,
            approved_reward_amount=latest_history.approved_reward_amount if latest_history else None,
            reward_credited_at=latest_history.credit_date if latest_history else None,
            reward_approved_by=latest_history.approved_by_account_id if latest_history else None,
            reward_approved_by_name=approved_by.name if approved_by else None,
            reward_approved_by_profile_image=approved_by.profile_pic if approved_by else None,
            booking_window_days=referral.booking_window_days,
            status=referral.status,
            notes=referral.notes,
        )

    def get_referral_or_404(self, referral_id: uuid.UUID) -> Referral:
        referral = self.repo.get_referral(referral_id)
        if referral is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found.")
        return referral

    def list_referrals(
        self,
        *,
        page: int,
        page_size: int,
        status: ReferralStatus | None,
        search: str | None,
    ) -> tuple[list[ReferralListItemResponse], int]:
        referrals, total_items = self.repo.list_referrals(
            status=status,
            search=search,
            page=page,
            page_size=page_size,
        )
        return [self._referral_to_list_item(item) for item in referrals], total_items

    def update_referral(
        self,
        *,
        referral_id: uuid.UUID,
        payload: ReferralManualUpdateRequest,
        current_user: Account,
    ) -> None:
        referral = self.get_referral_or_404(referral_id)
        if (
            payload.status == ReferralStatus.REWARD_CREDITED
            and referral.status != ReferralStatus.REWARD_CREDITED
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referral rewards are credited only after approval and eligibility checks.",
            )
        latest_history = self._latest_reward_history(referral)
        if payload.status is not None:
            referral.status = payload.status
            if payload.status == ReferralStatus.BOOKING_COMPLETED and referral.booking_completed_at is None:
                referral.booking_completed_at = datetime.now(timezone.utc)
            if payload.status == ReferralStatus.BOOKING_COMPLETED and referral.converted_at is None:
                referral.converted_at = datetime.now(timezone.utc)
        if payload.reward_amount is not None:
            if latest_history is None:
                latest_history = ReferralRewardHistory(
                    referral=referral,
                    approved_reward_amount=Decimal(str(payload.reward_amount)),
                    approved_by_account_id=current_user.id,
                )
                self.db.add(latest_history)
            else:
                latest_history.approved_reward_amount = Decimal(str(payload.reward_amount))
        if payload.notes is not None:
            referral.notes = payload.notes
        if referral.status == ReferralStatus.REWARD_APPROVED and latest_history is None:
            latest_history = ReferralRewardHistory(
                referral=referral,
                approved_reward_amount=(
                    referral.default_reward_amount
                    if referral.default_reward_amount is not None
                    else Decimal("500.00")
                ),
                approved_by_account_id=current_user.id,
            )
            self.db.add(latest_history)
        if referral.status == ReferralStatus.REWARD_CREDITED:
            self._credit_referral_reward(referral, current_user.id)
            return
        self.db.commit()
        if payload.status == ReferralStatus.REWARD_APPROVED:
            self.process_eligible_rewards(referral_id=referral.id)

    def process_eligible_rewards(
        self,
        referral_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        candidate_ids = self.repo.list_reward_candidate_ids(referral_id=referral_id)
        credited = 0
        skipped = 0
        failed = 0

        for referral_id in candidate_ids:
            try:
                referral = self.repo.get_for_reward_processing(referral_id)
                if (
                    referral is None
                    or referral.status
                    not in {
                        ReferralStatus.REGISTERED,
                        ReferralStatus.BOOKING_COMPLETED,
                        ReferralStatus.REWARD_ELIGIBLE,
                        ReferralStatus.REWARD_APPROVED,
                    }
                    or referral.referred_customer is None
                ):
                    skipped += 1
                    continue

                eligible_bookings = [
                    booking
                    for booking in referral.referred_customer.bookings
                    if booking.status == BookingStatus.COMPLETED
                    and self._booking_is_within_referral_window(referral, booking)
                ]
                if not eligible_bookings:
                    skipped += 1
                    continue

                booking = min(eligible_bookings, key=lambda item: item.created_at)
                completion_dates = [
                    history.changed_at
                    for history in booking.status_history
                    if history.new_status == BookingStatus.COMPLETED
                ]
                referral.booking_completed_at = (
                    referral.booking_completed_at
                    or min(completion_dates, default=booking.updated_at)
                )
                if referral.converted_at is None:
                    referral.converted_at = referral.booking_completed_at
                if referral.status != ReferralStatus.REWARD_APPROVED:
                    referral.status = ReferralStatus.REWARD_ELIGIBLE
                    self.db.commit()
                    skipped += 1
                    continue
                self.db.commit()

                self._credit_referral_reward(referral)
                credited += 1
            except Exception:
                self.db.rollback()
                logger.exception("Failed to process referral reward %s", referral_id)
                failed += 1

        return {"credited": credited, "skipped": skipped, "failed": failed}

    @staticmethod
    def _booking_is_within_referral_window(
        referral: Referral,
        booking: Booking,
    ) -> bool:
        referral_created_at = referral.created_at
        booking_created_at = booking.created_at
        referral_created_at_utc = (
            referral_created_at.replace(tzinfo=timezone.utc)
            if referral_created_at.tzinfo is None
            else referral_created_at.astimezone(timezone.utc)
        )
        booking_created_at_utc = (
            booking_created_at.replace(tzinfo=timezone.utc)
            if booking_created_at.tzinfo is None
            else booking_created_at.astimezone(timezone.utc)
        )
        booking_window_days = (
            30 if referral.booking_window_days is None else referral.booking_window_days
        )
        return (
            referral_created_at_utc
            <= booking_created_at_utc
            <= referral_created_at_utc + timedelta(days=booking_window_days)
        )

    def _credit_referral_reward(
        self,
        referral: Referral,
        approved_by_account_id: uuid.UUID | None = None,
    ) -> None:
        latest_history = self._latest_reward_history(referral)
        amount = latest_history.approved_reward_amount if latest_history else referral.default_reward_amount
        if amount is None:
            amount = Decimal("500.00")
        transaction = WalletService(self.db).credit_referral_reward(
            customer_id=referral.referrer_customer_id,
            referral_id=referral.id,
            amount=amount,
            description=f"Referral reward for referral {referral.id}",
        )
        if transaction.status != FinancialTransactionStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The referral reward transaction is not completed.",
            )

        if latest_history is None:
            latest_history = ReferralRewardHistory(
                referral_id=referral.id,
                approved_reward_amount=amount,
                approved_by_account_id=approved_by_account_id,
            )
            self.db.add(latest_history)
        latest_history.credit_date = transaction.transaction_date
        referral.status = ReferralStatus.REWARD_CREDITED
        if referral.booking_completed_at is None:
            referral.booking_completed_at = datetime.now(timezone.utc)
        if referral.converted_at is None:
            referral.converted_at = referral.booking_completed_at
        self.db.commit()

    def get_referral_config(self) -> ReferralRewardConfigResponse:
        config = self.repo.get_or_create_config()
        updated_by = config.updated_by
        return ReferralRewardConfigResponse(
            id=config.id,
            default_reward_amount=config.default_reward_amount,
            booking_window_days=config.booking_window_days,
            updated_by=config.updated_by_account_id,
            updated_by_name=updated_by.name if updated_by else None,
            updated_by_profile_image=updated_by.profile_pic if updated_by else None,
            updated_at=config.updated_at,
        )

    def update_referral_config(
        self,
        *,
        payload: ReferralRewardConfigRequest,
        current_user: Account,
    ) -> ReferralRewardConfigResponse:
        config = self.repo.get_or_create_config(
            default_reward_amount=payload.default_reward_amount,
            booking_window_days=payload.booking_window_days,
            admin=current_user,
        )
        updated_by = config.updated_by
        return ReferralRewardConfigResponse(
            id=config.id,
            default_reward_amount=config.default_reward_amount,
            booking_window_days=config.booking_window_days,
            updated_by=config.updated_by_account_id,
            updated_by_name=updated_by.name if updated_by else None,
            updated_by_profile_image=updated_by.profile_pic if updated_by else None,
            updated_at=config.updated_at,
        )

