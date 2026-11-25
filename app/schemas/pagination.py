"""Reusable pagination schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata about the current page of results."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_page": 1,
                "page_size": 20,
                "total_items": 42,
                "total_pages": 3,
                "has_next": True,
                "has_previous": False,
            }
        }
    )

    current_page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items matching the query")
    total_pages: int = Field(..., description="Total number of pages available")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_previous: bool = Field(..., description="Whether a previous page exists")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Items fetched successfully.",
                "data": [],
                "pagination": {
                    "current_page": 1,
                    "page_size": 20,
                    "total_items": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    success: bool = Field(default=True, description="Always true for a successful paginated response.")
    message: str = Field(default="Items fetched successfully.", description="Human-readable success message.")
    data: list[T] = Field(..., description="List of resources for the current page.")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

