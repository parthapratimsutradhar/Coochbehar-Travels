import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.db.database import get_db
from app.models.account import Account
from app.schemas.destination import DestinationCreate, DestinationResponse, DestinationUpdate
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.destination_service import DestinationService

router = APIRouter(
    prefix="/admin/destinations",
    tags=["Admin - Destinations"],
)


@router.post(
    "",
    response_model=SuccessResponse[DestinationResponse],
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Create a new destination",
)
def create_destination(
    payload: DestinationCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = DestinationService(db)
    destination = service.create_destination(payload)
    return SuccessResponse(
        message="Destination created successfully",
        data=DestinationResponse.model_validate(destination),
    )


@router.get(
    "",
    response_model=PaginatedResponse[DestinationResponse],
    summary="List destinations (Admin)",
)
def list_destinations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_domestic: bool | None = Query(None),
    is_featured: bool | None = Query(None),
    is_popular: bool | None = Query(None),
    is_active: bool | None = Query(None, description="Filter by active status. Admin can see inactive destinations."),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = DestinationService(db)
    result = service.list_destinations(
        page=page, page_size=page_size,
        is_domestic=is_domestic, is_featured=is_featured,
        is_popular=is_popular, is_active=is_active, search=search,
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
    "/{destination_id}",
    response_model=SuccessResponse[DestinationResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Get destination detail",
)
def get_destination(
    destination_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = DestinationService(db)
    destination = service.get_destination(destination_id)
    return SuccessResponse(
        message="Destination fetched successfully",
        data=DestinationResponse.model_validate(destination),
    )


@router.patch(
    "/{destination_id}",
    response_model=SuccessResponse[DestinationResponse],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Update a destination",
)
def update_destination(
    destination_id: uuid.UUID,
    payload: DestinationUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = DestinationService(db)
    destination = service.update_destination(destination_id, payload)
    return SuccessResponse(
        message="Destination updated successfully",
        data=DestinationResponse.model_validate(destination),
    )


@router.delete(
    "/{destination_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Soft-delete a destination",
)
def delete_destination(
    destination_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = DestinationService(db)
    service.delete_destination(destination_id)
    return ActionResponse(message="Destination deleted successfully")
