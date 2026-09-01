from typing import Any, Generic, TypeVar

from pydantic import Field
from app.schemas.base import SchemaBase

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response — non-paginated data object or list."""

    success: bool = Field(default=True)
    message: str
    data: T


class ActionResponse(SchemaBase):
    """Success response for DELETE, PUT, PATCH or actions with no data body content."""

    success: bool = Field(default=True)
    message: str


class ValidationErrorDetail(SchemaBase):
    field: str
    message: str


class ErrorPayload(SchemaBase):
    code: str
    details: Any | None = None


class ErrorResponse(SchemaBase):
    """Standard error response structure."""

    success: bool = Field(default=False)
    message: str
    error: ErrorPayload

