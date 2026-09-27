import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import PaymentMethod, ReferralStatus
from app.core.messages.error import ReferralError
from app.models.account import Account
from app.models.referral import Referral
from app.models.referral_reward_history import ReferralRewardHistory
from app.repository.referral_repo import ReferralRepository
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


class ReferralService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReferralRepository(db)

    def validate_invite(self, referral_code: str) -> ReferralInviteResponse:
        normalized_code = referral_code.strip().upper()
        referrer_profile = self.repo.get_profile_by_code(normalized_code)
        if referrer_profile is None or referrer_profile.account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ReferralError.INVALID_CODE,
            )
        return ReferralInviteResponse(
            referral_code=referrer_profile.referral_code,
            referrer_name=referrer_profile.account.name,
        )

    def get_customer_referral_code(self, customer_id: uuid.UUID) -> ReferralCodeResponse:
        profile = self.repo.get_profile_by_account_id(customer_id)
        return ReferralCodeResponse(referral_code=profile.referral_code if profile else "")

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
        latest_history = self._latest_reward_history(referral)
        approved_by = latest_history.approved_by if latest_history else None
        return ReferralListItemResponse(
            id=referral.id,
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
        if payload.status is not None:
            referral.status = payload.status
            if payload.status == ReferralStatus.BOOKING_COMPLETED and referral.booking_completed_at is None:
                referral.booking_completed_at = datetime.now(timezone.utc)
            if payload.status == ReferralStatus.BOOKING_COMPLETED and referral.converted_at is None:
                referral.converted_at = datetime.now(timezone.utc)
        if payload.reward_amount is not None:
            latest_history = self._latest_reward_history(referral)
            if latest_history is None:
                self.db.add(
                    ReferralRewardHistory(
                        referral_id=referral.id,
                        approved_reward_amount=Decimal(str(payload.reward_amount)),
                        approved_by_account_id=current_user.id,
                    )
                )
            else:
                latest_history.approved_reward_amount = Decimal(str(payload.reward_amount))
        if payload.notes is not None:
            referral.notes = payload.notes
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

