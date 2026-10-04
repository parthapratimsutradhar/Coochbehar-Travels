from typing import Literal

from pydantic import Field, model_validator
from app.schemas.base import SchemaBase

from app.core.enums import AccountRole


class AdminStaffCreate(SchemaBase):
    name: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    mobile: str | None = Field(default=None, min_length=3, max_length=20)
    role: Literal[AccountRole.ADMIN, AccountRole.STAFF] = Field(default=AccountRole.STAFF)
    profile_pic: str | None = Field(default=None, max_length=500)
    is_active: bool = True

    @model_validator(mode="after")
    def require_email_or_mobile(self):
        if self.email is None and self.mobile is None:
            raise ValueError("Either email or mobile is required")
        return self


class AdminProfileUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    mobile: str | None = Field(default=None, min_length=3, max_length=20)
    role: AccountRole | None = None
    profile_pic: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class AdminDeleteProfileRequest(SchemaBase):
    identifier: str = Field(..., min_length=3, max_length=255)
    otp: str = Field(..., min_length=4, max_length=10)

