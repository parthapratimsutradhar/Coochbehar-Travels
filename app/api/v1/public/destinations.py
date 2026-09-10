import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.destination import DestinationResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ErrorResponse, SuccessResponse
from app.services.destination_service import DestinationService

router = APIRouter(
    prefix="/public/destinations",
    tags=["Public - Destinations"],
)


@router.get(
    "",
    response_model=PaginatedResponse[DestinationResponse],
    summary="List active destinations (Public)",
)
def list_destinations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_domestic: bool | None = Query(None),
    is_featured: bool | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    service = DestinationService(db)
    result = service.list_destinations(
        page=page, page_size=page_size,
        is_domestic=is_domestic, is_featured=is_featured,
        is_active=True, search=search,
    )
    return PaginatedResponse(
        message="Destinations fetched successfully",
        data=[DestinationResponse.model_validate(d) for d in result["items"]],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )


@router.get(
    "/{slug}",
    response_model=SuccessResponse[DestinationResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Get destination by slug (Public)",
)
def get_destination_by_slug(
    slug: str,
    db: Session = Depends(get_db),
):
    service = DestinationService(db)
    destination = service.get_by_slug(slug)
    return SuccessResponse(
        message="Destination fetched successfully",
        data=DestinationResponse.model_validate(destination),
    )
