import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.enums import ReferralStatus
from app.models.account import Account
from app.models.customer_profile import CustomerProfile
from app.models.referral import Referral
from app.models.referral_config import ReferralRewardConfig
from app.models.referral_reward_history import ReferralRewardHistory


class ReferralRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile_by_code(self, referral_code: str) -> CustomerProfile | None:
        return (
            self.db.query(CustomerProfile)
            .options(joinedload(CustomerProfile.account))
            .filter(func.upper(CustomerProfile.referral_code) == referral_code.strip().upper())
            .first()
        )

    def get_profile_by_account_id(self, account_id: uuid.UUID) -> CustomerProfile | None:
        return self.db.query(CustomerProfile).filter(
            CustomerProfile.account_id == account_id,
        ).one_or_none()

    def get_referral(self, referral_id: uuid.UUID) -> Referral | None:
        return (
            self.db.query(Referral)
            .options(
                joinedload(Referral.referrer).joinedload(Account.customer_profile),
                joinedload(Referral.referred_customer).joinedload(Account.customer_profile),
                joinedload(Referral.reward_history),
            )
            .filter(Referral.id == referral_id)
            .first()
        )

    def list_referrals(
        self,
        *,
        status: ReferralStatus | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Referral], int]:
        query = (
            self.db.query(Referral)
            .options(
                joinedload(Referral.referrer).joinedload(Account.customer_profile),
                joinedload(Referral.referred_customer).joinedload(Account.customer_profile),
                joinedload(Referral.reward_history).joinedload(ReferralRewardHistory.approved_by),
            )
            .order_by(Referral.created_at.desc())
        )
        if status is not None:
            query = query.filter(Referral.status == status)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(or_(Referral.notes.ilike(term)))

        total_items = query.count()
        referrals = query.offset((page - 1) * page_size).limit(page_size).all()
        return referrals, total_items

    def list_customer_history(
        self,
        referrer_customer_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[Referral], int]:
        query = (
            self.db.query(Referral)
            .options(
                joinedload(Referral.referrer).joinedload(Account.customer_profile),
                joinedload(Referral.referred_customer).joinedload(Account.bookings),
                joinedload(Referral.reward_history),
            )
            .filter(Referral.referrer_customer_id == referrer_customer_id)
            .order_by(Referral.created_at.desc())
        )
        total_items = query.count()
        referrals = query.offset((page - 1) * page_size).limit(page_size).all()
        return referrals, total_items

    def get_latest_config(self) -> ReferralRewardConfig | None:
        return (
            self.db.query(ReferralRewardConfig)
            .options(joinedload(ReferralRewardConfig.updated_by))
            .order_by(ReferralRewardConfig.created_at.desc())
            .first()
        )

    def get_or_create_config(
        self,
        *,
        default_reward_amount: Decimal | None = None,
        booking_window_days: int | None = None,
        admin: Account | None = None,
    ) -> ReferralRewardConfig:
        config = self.get_latest_config()
        if config is None:
            config = ReferralRewardConfig(
                default_reward_amount=Decimal(str(default_reward_amount or "500.00")),
                booking_window_days=int(booking_window_days or 30),
                updated_by_account_id=admin.id if admin else None,
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            return config

        if default_reward_amount is not None:
            config.default_reward_amount = Decimal(str(default_reward_amount))
        if booking_window_days is not None:
            config.booking_window_days = int(booking_window_days)
        config.updated_by_account_id = admin.id if admin else config.updated_by_account_id
        config.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(config)
        return config
