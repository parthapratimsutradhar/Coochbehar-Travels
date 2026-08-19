from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response — non-paginated data object or list."""

    success: bool = Field(default=True)
    message: str
    data: T


class ActionResponse(BaseModel):
    """Success response for DELETE, PUT, PATCH or actions with no data body content."""

    success: bool = Field(default=True)
    message: str


class ValidationErrorDetail(BaseModel):
    field: str
    message: str


class ErrorPayload(BaseModel):
    code: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Standard error response structure."""

    success: bool = Field(default=False)
    message: str
    error: ErrorPayload

