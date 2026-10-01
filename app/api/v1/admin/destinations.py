import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.db.database import get_db
from app.models.account import Account
from app.schemas.destination import (
    AdminDestinationResponse,
    DestinationBulkTransferRequest,
    DestinationBulkTransferResponse,
    DestinationCreate,
    DestinationUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.destination_service import DestinationService

router = APIRouter(
    prefix="/admin/destinations",
    tags=["Admin - Destinations"],
)


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Create a new destination",
)
async def create_destination(
    payload: DestinationCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = DestinationService(db)
    await service.create_destination(payload)
    return ActionResponse(message="Destination created successfully")


@router.get(
    "",
    response_model=PaginatedResponse[AdminDestinationResponse],
    summary="List destinations (Admin)",
)
def list_destinations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_domestic: bool | None = Query(None),
    is_featured: bool | None = Query(None),
    is_active: bool | None = Query(None, description="Filter by active status. Admin can see inactive destinations."),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = DestinationService(db)
    result = service.list_destinations(
        page=page, page_size=page_size,
        is_domestic=is_domestic, is_featured=is_featured,
        is_active=is_active, search=search,
    )
    usage_counts = service.get_usage_counts([destination.id for destination in result["items"]])
    return PaginatedResponse(
        message="Destinations fetched successfully",
        data=[
            AdminDestinationResponse.model_validate(destination).model_copy(
                update=usage_counts[destination.id]
            )
            for destination in result["items"]
        ],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )


@router.post(
    "/bulk-transfer",
    response_model=SuccessResponse[DestinationBulkTransferResponse],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Transfer hotels and tour packages between destinations",
)
def bulk_transfer_destination_usage(
    payload: DestinationBulkTransferRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    data = DestinationService(db).bulk_transfer(payload)
    return SuccessResponse(
        message="Destination items transferred successfully",
        data=data,
    )


@router.patch(
    "/{destination_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Update a destination",
)
async def update_destination(
    destination_id: uuid.UUID,
    payload: DestinationUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = DestinationService(db)
    await service.update_destination(destination_id, payload)
    return ActionResponse(message="Destination updated successfully")


@router.delete(
    "/{destination_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
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
