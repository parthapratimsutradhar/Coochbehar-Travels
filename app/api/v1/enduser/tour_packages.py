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
from app.schemas.tour_package import (
    TourPackageDetailResponse,
    TourPackageFilterParams,
    TourPackageListItem,
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
    response_model=TourPackageDetailResponse,
    summary="Get tour package details by slug",
    description=(
        "Retrieve the full details of a tour package including all its "
        "variants and their associated tour details (banner, gallery, "
        "highlights, inclusions, exclusions, itinerary, departure dates, "
        "and route stops)."
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
    return service.get_package_by_slug(slug)
