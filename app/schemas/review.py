import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    """Review submitted by an authenticated customer for an eligible tour."""

    package_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    review: str = Field(..., min_length=1, max_length=5000)
    review_gallery: list[Any] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    id: uuid.UUID
    review_code: str
    package_id: uuid.UUID
    customer_id: uuid.UUID
    name: str
    rating: int
    review: str
    review_gallery: list[Any] = Field(default_factory=list)
    is_verified: bool
    is_published: bool
    created_at: datetime

    model_config = {"from_attributes": True}
