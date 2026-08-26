import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.core.enums import ReferralStatus


class ReferralCodeResponse(BaseModel):
    referral_code: str


class ReferralInviteResponse(BaseModel):
    referral_code: str
    referrer_name: str


class ReferredCustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_code: str
    name: str
    email: str | None = None
    mobile: str | None = None


class ReferralHistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    referral_code: str
    status: ReferralStatus
    reward_amount: Decimal | None = None
    reward_issued_at: datetime | None = None
    converted_at: datetime | None = None
    created_at: datetime
    referred_customer: ReferredCustomerResponse