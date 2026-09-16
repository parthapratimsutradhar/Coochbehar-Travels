import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict
from app.schemas.base import SchemaBase

from app.core.enums import ReferralStatus


class ReferralCodeResponse(SchemaBase):
    referral_code: str


class ReferralInviteResponse(SchemaBase):
    referral_code: str
    referrer_name: str


class ReferredCustomerResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_code: str
    name: str
    email: str | None = None
    mobile: str | None = None


class ReferralHistoryItemResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    referral_code: str
    status: ReferralStatus
    reward_amount: Decimal | None = None
    reward_issued_at: datetime | None = None
    converted_at: datetime | None = None
    created_at: datetime
    referred_customer: ReferredCustomerResponse


class ReferralRewardConfigRequest(SchemaBase):
    default_reward_amount: Decimal | None = None
    booking_window_days: int | None = None


class ReferralRewardConfigResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    default_reward_amount: Decimal
    booking_window_days: int
    updated_by: uuid.UUID | None = None
    updated_by_name: str | None = None
    updated_by_profile_image: str | None = None
    updated_at: datetime | None = None


class ReferralListItemResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    referrer_id: uuid.UUID | None = None
    referrer_name: str | None = None
    referrer_profile_image: str | None = None
    referrer_code: str | None = None
    referred_customer_id: uuid.UUID | None = None
    referred_customer_name: str | None = None
    referred_customer_profile_image: str | None = None
    referred_customer_code: str | None = None
    converted_at: datetime | None = None
    booking_completed_at: datetime | None = None
    default_reward_amount: Decimal | None = None
    approved_reward_amount: Decimal | None = None
    reward_credited_at: datetime | None = None
    reward_approved_by: uuid.UUID | None = None
    reward_approved_by_name: str | None = None
    reward_approved_by_profile_image: str | None = None
    booking_window_days: int | None = None
    status: ReferralStatus
    notes: str | None = None


class ReferralManualUpdateRequest(SchemaBase):
    status: ReferralStatus | None = None
    reward_amount: Decimal | None = None
    notes: str | None = None

