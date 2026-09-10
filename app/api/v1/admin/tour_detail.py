import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_admin_only
from app.db.database import get_db
from app.models.account import Account
from app.schemas.admin_tour import (
    AdminTourDetailPayload,
    TourDetailCreateRequest,
    TourDetailUpdateRequest,
)
from app.schemas.response import ActionResponse, SuccessResponse
from app.services.admin_tour_service import AdminTourService


router = APIRouter(prefix="/admin/tour-details", tags=["Admin Tour Details"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[AdminTourDetailPayload],
    summary="Create tour variant details",
)
def create_admin_tour_detail(
    payload: TourDetailCreateRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    detail = service.create_detail(payload.model_dump())
    return SuccessResponse(
        message="Tour details created successfully",
        data=service._detail_to_response(
            detail,
            detail.variant.package_id,
            service.get_variant_departures(detail.variant_id),
        ),
    )


@router.patch(
    "/{detail_id}",
    response_model=SuccessResponse[AdminTourDetailPayload],
    summary="Update tour variant details",
)
def update_admin_tour_detail(
    detail_id: uuid.UUID,
    payload: TourDetailUpdateRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    detail = service.update_detail(detail_id, payload.model_dump(exclude_unset=True))
    return SuccessResponse(
        message="Tour details updated successfully",
        data=service._detail_to_response(
            detail,
            detail.variant.package_id,
            service.get_variant_departures(detail.variant_id),
        ),
    )


@router.delete(
    "/{detail_id}",
    response_model=ActionResponse,
    summary="Delete tour variant details",
)
def delete_admin_tour_detail(
    detail_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).delete_detail(detail_id)
    return ActionResponse(message="Tour details deleted successfully")
