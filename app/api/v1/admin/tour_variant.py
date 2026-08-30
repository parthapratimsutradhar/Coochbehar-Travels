import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_admin_only
from app.db.database import get_db
from app.models.user import User
from app.schemas.admin_tour import (
    AdminTourVariantItem,
    TourVariantCreateRequest,
    TourVariantUpdateRequest,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, SuccessResponse
from app.services.admin_tour_service import AdminTourService


router = APIRouter(prefix="/admin/tour-variants", tags=["Admin Tour Variants"])


@router.get(
    "",
    response_model=PaginatedResponse[AdminTourVariantItem],
    summary="List all active/inactive tour variants",
)
def list_admin_tour_variants(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    tour_id: uuid.UUID | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    result = service.list_variants(tour_id=tour_id, page=page, page_size=page_size, is_active=is_active)
    return PaginatedResponse(
        message="Items fetched successfully",
        data=result["items"],
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
    "/{variant_id}",
    response_model=SuccessResponse[AdminTourVariantItem],
    summary="Get one tour variant",
)
def get_admin_tour_variant(
    variant_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    variant = AdminTourService(db).get_variant(variant_id)
    return SuccessResponse(message="Item fetched successfully", data=AdminTourService._variant_to_response(variant))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ActionResponse,
    summary="Create a tour variant",
)
def create_admin_tour_variant(
    payload: TourVariantCreateRequest,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).create_variant(payload.model_dump())
    return ActionResponse(message="Tour variant created successfully")


@router.patch(
    "/{variant_id}",
    response_model=ActionResponse,
    summary="Update a tour variant",
)
def update_admin_tour_variant(
    variant_id: uuid.UUID,
    payload: TourVariantUpdateRequest,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).update_variant(variant_id, payload.model_dump(exclude_unset=True))
    return ActionResponse(message="Tour variant updated successfully")


@router.delete(
    "/{variant_id}",
    response_model=ActionResponse,
    summary="Delete a tour variant",
)
def delete_admin_tour_variant(
    variant_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).delete_variant(variant_id)
    return ActionResponse(message="Tour variant deleted successfully")
