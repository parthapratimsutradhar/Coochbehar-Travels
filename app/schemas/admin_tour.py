import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field, ConfigDict
from app.schemas.base import SchemaBase

from app.core.enums import TourType


class AdminTourPackageItem(SchemaBase):
    id: uuid.UUID
    tour_code: str
    slug: str
    title: str
    destination: str
    type: TourType
    description: str | None = None
    is_featured: bool = False
    is_active: bool = True

    model_config = {"from_attributes": True}


class AdminTourVariantItem(SchemaBase):
    id: uuid.UUID
    tour_id: uuid.UUID
    slug: str
    name: str
    season_name: str | None = None
    valid_from: str
    valid_to: str
    duration_days: int
    duration_nights: int
    price: float
    seats: int | None = None
    badge: str | None = None
    availability: str | None = None
    is_default: bool = False
    is_active: bool = True

    model_config = {"from_attributes": True}


class BannerPayload(SchemaBase):
    image: str | None = None
    video: str | None = None

    model_config = ConfigDict(extra="allow")


class GalleryItem(SchemaBase):
    id: str
    alt: str | None = None
    url: str
    type: str | None = None
    display_order: int | None = None

    model_config = ConfigDict(extra="allow")


class HighlightItem(SchemaBase):
    id: str
    text: str

    model_config = ConfigDict(extra="allow")


class DepartureDateItem(SchemaBase):
    id: str
    date: str

    model_config = ConfigDict(extra="allow")


class ItineraryItem(SchemaBase):
    id: str
    day: int
    title: str
    description: str | None = None

    model_config = ConfigDict(extra="allow")


class RouteItem(SchemaBase):
    id: str
    city: str
    nights: int

    model_config = ConfigDict(extra="allow")


class AdminTourDetailPayload(SchemaBase):
    id: uuid.UUID | None = None
    tour_id: uuid.UUID | None = None
    variant_id: uuid.UUID
    banner: BannerPayload | None = None
    gallery: list[GalleryItem] = Field(default_factory=list)
    highlights: list[HighlightItem] = Field(default_factory=list)
    inclusions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    departure_dates: list[DepartureDateItem] = Field(default_factory=list)
    itinerary: list[ItineraryItem] = Field(default_factory=list)
    route: list[RouteItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TourPackageCreateRequest(SchemaBase):
    tour_code: str = Field(..., min_length=1, max_length=20)
    slug: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    destination: str = Field(..., min_length=1, max_length=150)
    type: TourType = TourType.DOMESTIC
    description: str | None = None
    is_featured: bool = False
    is_active: bool = True


class TourPackageUpdateRequest(SchemaBase):
    tour_code: str | None = Field(default=None, min_length=1, max_length=20)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    destination: str | None = Field(default=None, min_length=1, max_length=150)
    type: TourType | None = None
    description: str | None = None
    is_featured: bool | None = None
    is_active: bool | None = None


class TourVariantCreateRequest(SchemaBase):
    tour_id: uuid.UUID
    slug: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=100)
    season_name: str | None = None
    valid_from: str = Field(..., description="YYYY-MM-DD")
    valid_to: str = Field(..., description="YYYY-MM-DD")
    duration_days: int = Field(..., ge=0)
    duration_nights: int = Field(..., ge=0)
    price: float = Field(..., ge=0)
    seats: int | None = Field(default=None, ge=0)
    badge: str | None = None
    availability: str | None = Field(default="AVAILABLE", max_length=20)
    is_default: bool = False
    is_active: bool = True


class TourVariantUpdateRequest(SchemaBase):
    slug: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    season_name: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    duration_days: int | None = Field(default=None, ge=0)
    duration_nights: int | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, ge=0)
    seats: int | None = Field(default=None, ge=0)
    badge: str | None = None
    availability: str | None = Field(default=None, max_length=20)
    is_default: bool | None = None
    is_active: bool | None = None


class TourDetailCreateRequest(SchemaBase):
    variant_id: uuid.UUID
    banner: BannerPayload | None = None
    gallery: list[GalleryItem] | None = Field(default=None)
    highlights: list[HighlightItem] | None = Field(default=None)
    inclusions: list[str] | None = Field(default=None)
    exclusions: list[str] | None = Field(default=None)
    departure_dates: list[DepartureDateItem] | None = Field(default=None)
    itinerary: list[ItineraryItem] | None = Field(default=None)
    route: list[RouteItem] | None = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "variant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "banner": {"image": "string", "video": "string"},
                "gallery": [
                    {
                        "id": "string",
                        "alt": "string",
                        "url": "string",
                        "type": "string",
                        "display_order": 1,
                        "additionalProperty": "anything",
                    }
                ],
                "highlights": [
                    {"id": "string", "text": "string", "additionalProperty": "anything"}
                ],
                "inclusions": ["string"],
                "exclusions": ["string"],
                "departure_dates": [
                    {"id": "string", "date": "2026-08-30", "additionalProperty": "anything"}
                ],
                "itinerary": [
                    {
                        "id": "string",
                        "day": 1,
                        "title": "string",
                        "description": "string",
                        "additionalProperty": "anything",
                    }
                ],
                "route": [
                    {"id": "string", "city": "string", "nights": 1, "additionalProperty": "anything"}
                ],
            }
        }
    )


class TourDetailUpdateRequest(SchemaBase):
    banner: BannerPayload | None = None
    gallery: list[GalleryItem] | None = None
    highlights: list[HighlightItem] | None = None
    inclusions: list[str] | None = None
    exclusions: list[str] | None = None
    departure_dates: list[DepartureDateItem] | None = None
    itinerary: list[ItineraryItem] | None = None
    route: list[RouteItem] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "banner": {"image": "string", "video": "string"},
                "gallery": [
                    {
                        "id": "string",
                        "alt": "string",
                        "url": "string",
                        "type": "string",
                        "display_order": 1,
                        "additionalProperty": "anything",
                    }
                ],
                "highlights": [
                    {"id": "string", "text": "string", "additionalProperty": "anything"}
                ],
                "inclusions": ["string"],
                "exclusions": ["string"],
                "departure_dates": [
                    {"id": "string", "date": "2026-08-30", "additionalProperty": "anything"}
                ],
                "itinerary": [
                    {
                        "id": "string",
                        "day": 1,
                        "title": "string",
                        "description": "string",
                        "additionalProperty": "anything",
                    }
                ],
                "route": [
                    {"id": "string", "city": "string", "nights": 1, "additionalProperty": "anything"}
                ],
            }
        }
    )


def normalize_json_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_json_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_json_payload(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
