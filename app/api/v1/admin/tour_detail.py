import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_admin_only
from app.db.database import get_db
from app.models.tour_variant import TourVariant
from app.models.user import User
from app.schemas.admin_tour import (
    AdminTourDetailPayload,
    TourDetailCreateRequest,
    TourDetailUpdateRequest,
)
from app.schemas.response import ActionResponse, SuccessResponse
from app.services.admin_tour_service import AdminTourService


router = APIRouter(prefix="/admin/tour-details", tags=["Admin Tour Details"])


@router.get(
    "/{detail_id}",
    response_model=SuccessResponse[AdminTourDetailPayload],
    summary="Get selected tour variant details",
)
def get_admin_tour_details(
    detail_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    detail = AdminTourService(db).get_detail_by_id(detail_id)
    variant = db.get(TourVariant, detail.variant_id)
    package_id = variant.package_id if variant else None
    return SuccessResponse(message="Item fetched successfully", data=AdminTourService._detail_to_response(detail, package_id))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ActionResponse,
    summary="Create tour variant details",
)
def create_admin_tour_detail(
    payload: TourDetailCreateRequest,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).create_detail(payload.model_dump())
    return ActionResponse(message="Tour details created successfully")


@router.patch(
    "/{detail_id}",
    response_model=ActionResponse,
    summary="Update tour variant details",
)
def update_admin_tour_detail(
    detail_id: uuid.UUID,
    payload: TourDetailUpdateRequest,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).update_detail(detail_id, payload.model_dump(exclude_unset=True))
    return ActionResponse(message="Tour details updated successfully")


@router.delete(
    "/{detail_id}",
    response_model=ActionResponse,
    summary="Delete tour variant details",
)
def delete_admin_tour_detail(
    detail_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).delete_detail(detail_id)
    return ActionResponse(message="Tour details deleted successfully")
