"""Pydantic schemas for tour package API serialization."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import TourType


# ── Media sub-schemas ───────────────────────────────────────────────

class BannerResponse(BaseModel):
    """Banner media returned for a package or variant."""

    image: str | None = None
    video: str | None = None


class TourPackageSelectionVariant(BaseModel):
    """Lightweight active variant used by package selectors."""

    id: uuid.UUID
    name: str
    season_name: str | None = None


class TourPackageSelectionItem(BaseModel):
    """Compact active package payload used when selecting a package."""

    id: uuid.UUID
    title: str
    banner: BannerResponse | None = None
    variants: list[TourPackageSelectionVariant] = Field(default_factory=list)


# ── Gallery sub-schema ───────────────────────────────────────────────

class GalleryItemResponse(BaseModel):
    id: str | None = None
    alt: str | None = None
    url: str
    type: str | None = None
    display_order: int | None = None

    model_config = {"extra": "allow"}


# ── Review sub-schema ────────────────────────────────────────────────

class ReviewItemResponse(BaseModel):
    """Review item attached at the package level."""

    id: uuid.UUID
    reviewer_by: str
    reviewer_pic: str | None = None
    name: str
    rating: int
    review: str
    review_gallery: list[GalleryItemResponse] = Field(default_factory=list)
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class VariantSummaryResponse(BaseModel):
    """Lightweight variant info used in package and variant responses."""

    slug: str
    name: str
    season_name: str | None = None
    badge: str | None = None
    availability: str | None = "AVAILABLE"

    model_config = {"from_attributes": True}


class RouteStopResponse(BaseModel):
    id: str | None = None
    city: str | None = None
    nights: int | None = None

    model_config = {"extra": "allow"}


class HighlightResponse(BaseModel):
    id: str | None = None
    text: str

    model_config = {"extra": "allow"}


class DepartureDateResponse(BaseModel):
    id: str | None = None
    date: date

    model_config = {"extra": "allow"}


class ItineraryItemResponse(BaseModel):
    id: str | None = None
    day: int | str
    title: str | None = None
    description: str | None = None

    model_config = {"extra": "allow"}


# ── Season / Variant Sub-Schema ─────────────────────────────────────

class TourSeasonResponse(BaseModel):
    """A seasonal variant of a tour package with its own route, itinerary, dates, and media."""

    id: uuid.UUID
    key: str | None = Field(None, description="Season identifier key e.g. tulip, summer, autumn")
    display_order: int | None = Field(None, description="Display sorting order")
    slug: str
    name: str
    badge: str | None = Field(None, description="Badge text e.g. Most Popular, Family Special")
    season_type: str | None = Field(None, description="Season category e.g. SPRING, SUMMER, AUTUMN")
    season_name: str | None = Field(None, description="Season title e.g. Tulip Season, Winter Special")
    cover_image: str | None = Field(None, description="Cover/Banner image URL for this season")
    valid_from: date
    valid_to: date
    duration: str | None = Field(None, description="Formatted duration e.g. '13N | 14D'")
    duration_days: int
    duration_nights: int
    price: float = Field(..., description="Base price for this season variant")
    currency: str = Field("INR", description="Currency symbol/code")
    starting_price: float | None = Field(None, description="Starting / base price")
    seats: int | None = None
    availability: str = Field("AVAILABLE", description="Availability status")
    is_active: bool = True
    is_default: bool | None = None

    # Season-specific details
    route: list[RouteStopResponse] = Field(default_factory=list)
    highlights: list[HighlightResponse] = Field(default_factory=list)
    dates: list[DepartureDateResponse] = Field(default_factory=list)
    gallery: list[GalleryItemResponse] = Field(default_factory=list)
    itinerary: list[ItineraryItemResponse] = Field(default_factory=list)
    inclusions: list[Any] = Field(default_factory=list, description="Inclusions list")
    exclusions: list[Any] = Field(default_factory=list, description="Exclusions list")

    model_config = {"from_attributes": True}


class TourPackageVariantDetailResponse(BaseModel):
    """Detailed variant payload for a package variant route."""

    id: uuid.UUID
    slug: str
    name: str
    badge: str | None = None
    season_name: str | None = None
    banner: BannerResponse | None = None
    valid_from: date
    valid_to: date
    duration_days: int
    duration_nights: int
    price: float = Field(..., description="Base price")
    seats: int | None = None
    availability: str = Field("AVAILABLE", description="Availability status")
    route: list[RouteStopResponse] = Field(default_factory=list)
    highlights: list[HighlightResponse] = Field(default_factory=list)
    departure_dates: list[DepartureDateResponse] = Field(default_factory=list)
    gallery: list[GalleryItemResponse] = Field(default_factory=list)
    itinerary: list[ItineraryItemResponse] = Field(default_factory=list)
    inclusions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── Tour Package Schemas ─────────────────────────────────────────────

class TourPackageListItem(BaseModel):
    """Representation used in paginated public list responses."""

    id: uuid.UUID
    tour_code: str
    slug: str
    title: str
    destination: str
    type: TourType
    description: str | None = None
    season_name: str | None = None
    badge: str | None = None
    banner: BannerResponse | None = None
    is_featured: bool    
    is_wishlist: bool = False

    model_config = {"from_attributes": True}


class TourPackageDetailResponse(BaseModel):
    """Full tour package response with selected/default variant payloads."""

    id: uuid.UUID
    tour_code: str
    slug: str
    title: str
    destination: str
    type: TourType
    description: str | None = None
    is_wishlist: bool = False
    default_variant: TourPackageVariantDetailResponse | None = None
    other_variants: list[VariantSummaryResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TourPackageVariantDetailPayload(BaseModel):
    """Payload returned by the /{package_slug}/variants/{variant_slug} route."""

    variant: TourPackageVariantDetailResponse
    other_variants: list[VariantSummaryResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── Filter schema ────────────────────────────────────────────────────

class TourPackageFilterParams(BaseModel):
    """Query-string filters for the list tour packages endpoint."""

    destination: str | None = Field(
        None,
        description="Filter by destination (case-insensitive partial match)",
    )
    type: TourType | None = Field(
        None,
        description="Filter by tour type: DOMESTIC or INTERNATIONAL",
    )
    season: str | None = Field(
        None,
        description="Filter by active variant season name (case-insensitive)",
    )
    is_featured: bool | None = Field(
        None,
        description="Filter by featured status",
    )
    is_active: bool | None = Field(
        None,
        description="Filter by active status",
    )
    min_price: float | None = Field(
        None,
        ge=0,
        description="Minimum starting price filter",
    )
    max_price: float | None = Field(
        None,
        ge=0,
        description="Maximum starting price filter",
    )
    search: str | None = Field(
        None,
        description="Search by title or destination (case-insensitive)",
    )
    sort_by: str = Field(
        "created_at",
        description="Sort field: created_at, title, destination, starting_price",
    )
    sort_order: str = Field(
        "desc",
        description="Sort direction: asc or desc",
    )
