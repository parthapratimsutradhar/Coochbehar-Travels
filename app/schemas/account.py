from pydantic import Field
from app.schemas.base import SchemaBase

from app.core.enums import UserRole


class AdminProfileUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    mobile: str | None = Field(default=None, min_length=3, max_length=20)
    role: UserRole | None = None
    profile_pic: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class AdminDeleteProfileRequest(SchemaBase):
    identifier: str = Field(..., min_length=3, max_length=255)
    otp: str = Field(..., min_length=4, max_length=10)


