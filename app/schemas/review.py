import uuid
from datetime import datetime

from pydantic import Field
from app.schemas.base import SchemaBase

from app.schemas.tour_package import GalleryItemResponse


class ReviewCreate(SchemaBase):
    """Review submitted by an authenticated customer for an eligible tour."""

    package_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    review: str = Field(..., min_length=1, max_length=5000)
    review_gallery: list[GalleryItemResponse] = Field(default_factory=list)


class ReviewUpdate(SchemaBase):
    """Fields an authenticated customer may edit on their review."""

    rating: int | None = Field(None, ge=1, le=5)
    review: str | None = Field(None, min_length=1, max_length=5000)
    review_gallery: list[GalleryItemResponse] | None = None


class ReviewResponse(SchemaBase):
    id: uuid.UUID
    package_id: uuid.UUID
    customer_id: uuid.UUID | None
    name: str
    rating: int
    review: str
    review_gallery: list[GalleryItemResponse] = Field(default_factory=list)
    is_verified: bool
    is_published: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewEligibilityResponse(SchemaBase):
    """Review actions available to the authenticated customer for a package."""

    package_id: uuid.UUID
    can_review: bool
    has_reviewed: bool
    review: ReviewResponse | None = None
