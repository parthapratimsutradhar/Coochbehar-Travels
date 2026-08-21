"""Tour Packages — public (end-user) API endpoints.

Provides paginated listing with filters and single-package detail
retrieval. These endpoints are read-only and do not require
authentication.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import TourType
from app.db.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.response import SuccessResponse, ErrorResponse
from app.schemas.tour_package import (
    TourPackageDetailResponse,
    TourPackageFilterParams,
    TourPackageListItem,
    TourPackageVariantDetailPayload,
)
from app.services.tour_package_service import TourPackageService

router = APIRouter(
    prefix="/tour-packages",
    tags=["Tour Packages"],
)


@router.get(
    "",
    response_model=PaginatedResponse[TourPackageListItem],
    summary="List all tour packages",
    description=(
        "Retrieve a paginated list of tour packages with optional filters "
        "for destination, type, featured status, price range, and free-text "
        "search. Each item includes the starting price (lowest active "
        "variant price), duration from the default variant, and the total "
        "count of active variants."
    ),
    responses={
        200: {
            "description": "Paginated list of tour packages",
        },
    },
)
def list_tour_packages(
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-indexed)",
    ),
    page_size: int = Query(
        10,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    destination: str | None = Query(
        None,
        description="Filter by destination (case-insensitive partial match)",
    ),
    type: TourType | None = Query(
        None,
        description="Filter by tour type: DOMESTIC or INTERNATIONAL",
    ),
    season: str | None = Query(
        None,
        description="Filter by variant season name (case-insensitive)",
    ),
    is_featured: bool | None = Query(
        None,
        description="Filter by featured status",
    ),
    is_active: bool | None = Query(
        None,
        description="Filter by active status (defaults to showing all)",
    ),
    min_price: float | None = Query(
        None,
        ge=0,
        description="Minimum starting price (inclusive)",
    ),
    max_price: float | None = Query(
        None,
        ge=0,
        description="Maximum starting price (inclusive)",
    ),
    search: str | None = Query(
        None,
        description="Free-text search across title and destination",
    ),
    sort_by: str = Query(
        "created_at",
        description="Sort field: created_at, title, destination, starting_price, updated_at",
    ),
    sort_order: str = Query(
        "desc",
        description="Sort direction: asc or desc",
    ),
    db: Session = Depends(get_db),
):
    """Return a paginated, filtered list of tour packages."""

    filters = TourPackageFilterParams(
        destination=destination,
        type=type,
        season=season,
        is_featured=is_featured,
        is_active=is_active,
        min_price=min_price,
        max_price=max_price,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    service = TourPackageService(db)
    return service.list_packages(page, page_size, filters)


@router.get(
    "/{slug}",
    response_model=SuccessResponse[TourPackageDetailResponse],
    summary="Get tour package details by slug",
    description=(
        "Retrieve the full details of a tour package including its default "
        "variant, other variants, and package reviews."
    ),
    responses={
        200: {"description": "Tour package with full variant details"},
        404: {"description": "Tour package not found"},
    },
)
def get_tour_package(
    slug: str,
    db: Session = Depends(get_db),
):
    """Fetch a single tour package by its URL slug."""

    service = TourPackageService(db)
    detail = service.get_package_by_slug(slug)
    return SuccessResponse(
        message="Tour package fetched successfully",
        data=detail,
    )


@router.get(
    "/{slug}/variants/{variant_slug}",
    response_model=SuccessResponse[TourPackageVariantDetailPayload],
    summary="Get a specific variant for a tour package",
    description="Return a single variant payload plus the remaining variants in the same package.",
    responses={
        200: {"description": "Specific tour variant details"},
        404: {"description": "Package or variant not found"},
    },
)
def get_tour_package_variant(
    slug: str,
    variant_slug: str,
    db: Session = Depends(get_db),
):
    """Fetch a specific package variant by package slug and variant slug."""

    service = TourPackageService(db)
    payload = service.get_variant_by_slug(slug, variant_slug)
    return SuccessResponse(
        message="Variant fetched successfully",
        data=payload,
    )

