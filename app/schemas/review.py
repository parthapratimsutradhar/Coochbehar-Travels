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


class AdminReviewGalleryItemCreate(SchemaBase):
    """Gallery item accepted when an administrator creates a review."""

    alt: str | None = None
    url: str
    type: str | None = None
    display_order: int | None = None


class AdminReviewCreate(SchemaBase):
    """Review an administrator can create for a package."""

    customer_id: uuid.UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    review: str = Field(..., min_length=1, max_length=5000)
    review_gallery: list[AdminReviewGalleryItemCreate] = Field(default_factory=list)
    is_published: bool = True


class AdminReviewUpdate(SchemaBase):
    """Fields an administrator may edit on a review."""

    customer_id: uuid.UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    rating: int | None = Field(None, ge=1, le=5)
    review: str | None = Field(None, min_length=1, max_length=5000)
    review_gallery: list[GalleryItemResponse] | None = None
    is_published: bool | None = None


class ReviewResponse(SchemaBase):
    id: uuid.UUID
    package_id: uuid.UUID
    customer_id: uuid.UUID | None
    customer_profile_picture: str | None = None
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
