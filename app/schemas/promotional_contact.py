from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, model_validator

from app.schemas.base import SchemaBase


class PromotionalContactFields(SchemaBase):
    name: str | None = None
    mobile: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None


class PromotionalContactCreate(PromotionalContactFields):
    @model_validator(mode="after")
    def require_contact_detail(self):
        if not any(value is not None for value in (self.name, self.mobile, self.email)):
            raise ValueError("At least one of name, mobile, or email is required")
        return self


class PromotionalContactUpdate(PromotionalContactFields):
    @model_validator(mode="before")
    @classmethod
    def require_update_fields(cls, values):
        if isinstance(values, dict) and not values:
            raise ValueError("At least one field must be provided")
        return values


class PromotionalContactResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    mobile: str | None
    email: str | None


class PromotionalContactImportResult(SchemaBase):
    imported_count: int
