from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.base import SchemaBase

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response — non-paginated data object or list."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Resource retrieved successfully.",
                "data": {},
            }
        }
    )

    success: bool = Field(default=True, description="Always true for a successful response.")
    message: str = Field(description="Human-readable success message.")
    data: T = Field(description="Requested resource, resource list, or operation result.")


class ActionResponse(BaseModel):
    """Success response for DELETE, PUT, PATCH or actions with no data body content."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully.",
            }
        },
    )

    success: bool = Field(default=True, description="Always true for a successful response.")
    message: str = Field(
        description="Human-readable confirmation of the completed operation.",
        examples=["Operation completed successfully."],
    )


class ValidationErrorDetail(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "field": "recipient_email",
                "message": "The email address is invalid.",
            }
        },
    )

    field: str = Field(description="Request field or nested field that failed validation.")
    message: str = Field(description="Human-readable validation error.")


class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str = Field(
        description="Stable machine-readable error code.",
        examples=["NOT_FOUND", "VALIDATION_ERROR", "CONFLICT"],
    )
    details: Any | None = Field(
        ...,
        description="Additional error details. For validation failures, this is a list of field errors; it is null when no extra details are available.",
        examples=[[
            {
                "field": "recipient_email",
                "message": "The email address is invalid.",
            }
        ]],
    )


class ErrorResponse(BaseModel):
    """Standard error response structure."""

    model_config = ConfigDict(extra="ignore")

    success: bool = Field(default=False, description="Always false for an error response.")
    message: str = Field(
        description="Human-readable error message.",
        examples=["Quotation not found.", "Request validation failed."],
    )
    error: ErrorPayload = Field(description="Machine-readable error code and optional details.")


def documented_error_response(
    *,
    description: str,
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    """Build an OpenAPI error response with an operation-relevant example."""
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": message,
                    "error": {
                        "code": code,
                        "details": details,
                    },
                }
            }
        },
    }

