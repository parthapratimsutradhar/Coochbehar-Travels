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
    name: str
    rating: int
    review: str
    is_verified: bool = False
    is_published: bool = True
    created_at: datetime | None = None

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


# ── Tour Package Schemas ─────────────────────────────────────────────

class TourPackageListItem(BaseModel):
    """Lightweight representation used in paginated list responses."""

    id: uuid.UUID
    tour_code: str
    slug: str
    title: str
    destination: str
    type: TourType
    description: str | None = None
    is_featured: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    starting_price: float | None = Field(
        None,
        description="Lowest base_price across active variants",
    )
    duration_days: int | None = Field(
        None,
        description="Duration days from the default variant",
    )
    duration_nights: int | None = Field(
        None,
        description="Duration nights from the default variant",
    )
    duration: str | None = Field(
        None,
        description="Formatted duration string (e.g. '13N | 14D')",
    )
    variant_count: int = Field(
        0,
        description="Total number of active variants/seasons",
    )

    model_config = {"from_attributes": True}


class TourPackageDetailResponse(BaseModel):
    """Full tour package response with package-level reviews and a list of seasonal variants (seasons)."""

    id: uuid.UUID
    tour_code: str
    slug: str
    title: str
    destination: str
    type: TourType
    description: str | None = None
    is_featured: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Package-level reviews
    reviews: list[ReviewItemResponse] = Field(default_factory=list, description="Reviews for this tour package")

    # Seasonal variants
    seasons: list[TourSeasonResponse] = Field(
        default_factory=list,
        description="Seasonal variants for this tour package, each with its own route, dates, itinerary & gallery",
    )

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
