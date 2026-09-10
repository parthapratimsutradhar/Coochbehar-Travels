import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.db.database import get_db
from app.models.account import Account
from app.schemas.admin_tour import (
    TourVariantCreateRequest,
    TourVariantUpdateRequest,
)

from app.schemas.response import ActionResponse
from app.services.admin_tour_service import AdminTourService


router = APIRouter(prefix="/admin/tour-variants", tags=["Admin Tour Variants"])

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ActionResponse,
    summary="Create a tour variant",
)
def create_admin_tour_variant(
    payload: TourVariantCreateRequest,
    current_user: Account = Depends(get_current_admin_only),
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
    current_user: Account = Depends(get_current_admin_only),
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
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).delete_variant(variant_id)
    return ActionResponse(message="Tour variant deleted successfully")
