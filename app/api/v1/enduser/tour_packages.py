"""Tour Packages — public (end-user) API endpoints.

Provides paginated listing with filters and single-package detail
retrieval. These endpoints are read-only and do not require
authentication.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import TourType
from app.api.deps import get_optional_customer
from app.db.database import get_db
from app.models.customer import Customer
from app.schemas.pagination import PaginatedResponse
from app.schemas.response import SuccessResponse, ErrorResponse
from app.schemas.tour_package import (
    TourPackageDetailResponse,
    TourPackageFilterParams,
    TourPackageListItem,
    TourPackageSelectionItem,
    TourPackageVariantDetailPayload,
)
from app.services.tour_package_service import TourPackageService

router = APIRouter(
    prefix="/tour-packages",
    tags=["Tour Packages"],
)


@router.get(
    "/select/{slug}",
    response_model=SuccessResponse[TourPackageSelectionItem],
    responses={422: {"model": ErrorResponse}},
    summary="Get a tour package for selection",
    description="Return one active package and its active variants for package selection.",
)
def list_packages_for_selection(
    slug: str,
    db: Session = Depends(get_db),
):
    """Return one compact active package for package selection."""

    service = TourPackageService(db)
    return SuccessResponse(
        message="Active package fetched successfully",
        data=service.get_package_for_selection(slug),
    )


@router.get(
    "",
    response_model=PaginatedResponse[TourPackageListItem],
    responses={422: {"model": ErrorResponse}},
    summary="List all tour packages",
    description=(
        "Retrieve a paginated list of tour packages with optional filters "
        "for destination, type, featured status, price range, and free-text "
        "search. Each item includes the starting price (lowest active "
        "variant price), duration from the default variant, and the total "
        "count of active variants."
    ),
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
    current_customer: Customer | None = Depends(get_optional_customer),
    db: Session = Depends(get_db),
):
    """Return a paginated, filtered list of tour packages."""

    filters = TourPackageFilterParams(
        destination=destination,
        type=type,
        season=season,
        is_featured=is_featured,
        is_active=True,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    service = TourPackageService(db)
    return service.list_packages(
        page,
        page_size,
        filters,
        customer_id=current_customer.id if current_customer else None,
    )


@router.get(
    "/{slug}",
    response_model=SuccessResponse[TourPackageDetailResponse],
    responses={422: {"model": ErrorResponse}},
    summary="Get tour package details by slug",
    description=(
        "Retrieve the full details of a tour package including its default "
        "variant and other variants. Fetch package reviews from the reviews endpoint."
    ),
)
def get_tour_package(
    slug: str,
    current_customer: Customer | None = Depends(get_optional_customer),
    db: Session = Depends(get_db),
):
    """Fetch a single tour package by its URL slug."""

    service = TourPackageService(db)
    detail = service.get_package_by_slug(
        slug,
        customer_id=current_customer.id if current_customer else None,
    )
    return SuccessResponse(
        message="Tour package fetched successfully",
        data=detail,
    )


@router.get(
    "/{slug}/variants/{variant_slug}",
    response_model=SuccessResponse[TourPackageVariantDetailPayload],
    responses={422: {"model": ErrorResponse}},
    summary="Get a specific variant for a tour package",
    description="Return a single variant payload plus the remaining variants in the same package.",
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

