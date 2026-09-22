import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.messages.success import VendorSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.schemas.vendor import VendorCreate, VendorResponse, VendorUpdate
from app.services.vendor_service import VendorService

router = APIRouter(
    prefix="/admin/vendors",
    tags=["Admin - Vendors"],
)


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
    summary="Create a new vendor",
)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    del current_user
    VendorService(db).create_vendor(payload)
    return ActionResponse(message=VendorSuccess.CREATED)


@router.get(
    "",
    response_model=PaginatedResponse[VendorResponse],
    summary="List vendors (Admin)",
)
def list_vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, description="Filter by vendor type (HOTEL, TRANSPORT, etc.)"),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    del current_user
    service = VendorService(db)
    result = service.list_vendors(page=page, page_size=page_size, type=type, search=search)
    return PaginatedResponse(
        message=VendorSuccess.RETRIEVED,
        data=[VendorResponse.model_validate(v) for v in result["items"]],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )


@router.patch(
    "/{vendor_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Update a vendor",
)
def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    del current_user
    VendorService(db).update_vendor(vendor_id, payload)
    return ActionResponse(message=VendorSuccess.UPDATED)


@router.delete(
    "/{vendor_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Delete a vendor",
)
def delete_vendor(
    vendor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
    del current_user
    VendorService(db).delete_vendor(vendor_id)
    return ActionResponse(message=VendorSuccess.DELETED)
