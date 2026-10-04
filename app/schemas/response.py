from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.base import SchemaBase

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response — non-paginated data object or list."""

    success: bool = Field(default=True)
    message: str
    data: T


class ActionResponse(BaseModel):
    """Success response for DELETE, PUT, PATCH or actions with no data body content."""

    model_config = ConfigDict(extra="ignore")

    success: bool = Field(default=True)
    message: str


class ValidationErrorDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str
    message: str


class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Standard error response structure."""

    model_config = ConfigDict(extra="ignore")

    success: bool = Field(default=False)
    message: str
    error: ErrorPayload

