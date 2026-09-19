from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.enums import FinancialAccountOwnerType, FinancialAccountType
from app.schemas.base import SchemaBase


class FinancialAccountCreate(SchemaBase):
    account_code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=150)
    account_type: FinancialAccountType
    owner_type: FinancialAccountOwnerType = FinancialAccountOwnerType.SYSTEM
    owner_id: UUID | None = None
    currency: str = Field(default="INR", min_length=3, max_length=3)


class FinancialAccountResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_code: str
    name: str
    account_type: FinancialAccountType
    owner_type: FinancialAccountOwnerType
    owner_id: UUID | None
    currency: str
    is_active: bool
