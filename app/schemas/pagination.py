"""Reusable pagination schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from app.schemas.base import SchemaBase

T = TypeVar("T")


class PaginationMeta(SchemaBase):
    """Metadata about the current page of results."""

    current_page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items matching the query")
    total_pages: int = Field(..., description="Total number of pages available")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_previous: bool = Field(..., description="Whether a previous page exists")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    success: bool = Field(default=True)
    message: str = Field(default="Items fetched successfully")
    data: list[T] = Field(..., description="List of items for the current page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

