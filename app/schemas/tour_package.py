"""Pydantic schemas for tour package API serialization."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import TourType


# ── Review sub-schema ────────────────────────────────────────────────

class ReviewItemResponse(BaseModel):
    """Review item attached at the package level."""

    id: uuid.UUID
    review_code: str
    reviewer_by: str
    reviewer_pic: str | None = None
    name: str
    rating: int
    review: str
    review_gallery: list[Any] = Field(default_factory=list)
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
    route: list[Any] = Field(default_factory=list, description="Route stops e.g. [{id: 'r1', place: 'Katra (2N)'}]")
    highlights: list[Any] = Field(default_factory=list, description="Highlights e.g. [{id: 'h1', text: 'Gondola ride'}]")
    dates: list[Any] = Field(default_factory=list, description="Departure dates e.g. [{id: 'd1', date: '23 Mar 2026'}]")
    gallery: list[Any] = Field(default_factory=list, description="Gallery photos e.g. [{id: 'g1', photoId: '...'}]")
    itinerary: list[Any] = Field(default_factory=list, description="Itinerary days e.g. [{id: 'i1', day: '...', description: '...'}]")
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
    banner: str | None = None
    valid_from: date
    valid_to: date
    duration_days: int
    duration_nights: int
    price: float = Field(..., description="Base price")
    seats: int | None = None
    availability: str = Field("AVAILABLE", description="Availability status")
    route: list[Any] = Field(default_factory=list)
    highlights: list[Any] = Field(default_factory=list)
    departure_dates: list[Any] = Field(default_factory=list)
    gallery: list[Any] = Field(default_factory=list)
    itinerary: list[Any] = Field(default_factory=list)
    inclusions: list[Any] = Field(default_factory=list)
    exclusions: list[Any] = Field(default_factory=list)

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
    banner: str | None = None

    model_config = {"from_attributes": True}


class TourPackageDetailResponse(BaseModel):
    """Full tour package response with package-level reviews and selected/default variant payloads."""

    id: uuid.UUID
    tour_code: str
    slug: str
    title: str
    destination: str
    type: TourType
    description: str | None = None
    reviews: list[ReviewItemResponse] = Field(default_factory=list, description="Reviews for this tour package")
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
