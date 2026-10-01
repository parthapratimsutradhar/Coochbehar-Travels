"""Tour Packages — public (end-user) API endpoints.

Provides paginated listing with filters and single-package detail
retrieval. These endpoints are read-only and do not require
authentication.
"""

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
    TourPackageSelectionItem,
    TourPackageVariantDetailPayload,
    TourPackageVariantListItem,
    TourDetailPayload,
)
from app.services.tour_package_service import TourPackageService

router = APIRouter(
    prefix="/tour-packages",
    tags=["Tour Packages"],
)


@router.get(
    "",
    response_model=PaginatedResponse[TourPackageListItem],
    summary="List tour packages",
)
def list_tour_packages(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    destination: str | None = Query(None),
    type: TourType | None = Query(None),
    season: str | None = Query(None),
    badge: str | None = Query(None),
    is_featured: bool | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    search: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[TourPackageListItem]:
    filters = TourPackageFilterParams(
        destination=destination,
        type=type,
        season=season,
        badge=badge,
        is_featured=is_featured,
        is_active=True,
        min_price=min_price,
        max_price=max_price,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return TourPackageService(db).list_packages(
        page=page,
        page_size=page_size,
        filters=filters,
    )


@router.get(
    "/{tour_slug}/variants",
    response_model=PaginatedResponse[TourPackageVariantListItem],
    summary="List variants for a tour package",
)
def list_tour_package_variants(
    tour_slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[TourPackageVariantListItem]:
    return TourPackageService(db).list_variants(
        package_slug=tour_slug,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{tour_slug}/variants/{variant_slug}/details",
    response_model=SuccessResponse[TourDetailPayload],
    summary="Get tour variant details",
)
def get_tour_variant_details(
    tour_slug: str,
    variant_slug: str,
    db: Session = Depends(get_db),
) -> SuccessResponse[TourDetailPayload]:
    return SuccessResponse(
        message="Tour details fetched successfully",
        data=TourPackageService(db).get_tour_detail(tour_slug, variant_slug),
    )

