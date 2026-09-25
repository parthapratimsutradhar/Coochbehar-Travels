import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_admin_only
from app.core.messages.success import TourDetailSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.admin_tour import (
    AdminTourDetailPayload,
    TourDetailCreateRequest,
    TourDetailUpdateRequest,
)
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.admin_tour_service import AdminTourService


router = APIRouter(prefix="/admin/tour-details", tags=["Admin Tour Details"])


@router.get(
    "/{detail_id}",
    response_model=SuccessResponse[AdminTourDetailPayload],
    responses={404: {"model": ErrorResponse}},
    summary="Get tour variant details",
)
def get_admin_tour_detail(
    detail_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    detail = service.get_detail_by_id(detail_id)
    variant = service.get_variant(detail.variant_id)
    returns = service.get_variant_departures(detail.variant_id)
    return SuccessResponse(
        message="Item fetched successfully",
        data=AdminTourService._detail_to_response(detail, variant.package_id, returns),
    )


@router.put(
    "",
    response_model=SuccessResponse[AdminTourDetailPayload],
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Create or update tour variant details",
)
async def upsert_admin_tour_detail(
    payload: TourDetailCreateRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    existing_detail = service.repo.get_detail_by_variant_id(payload.variant_id)
    detail = await service.upsert_detail(payload.model_dump())
    variant = service.get_variant(detail.variant_id)
    departures = service.get_variant_departures(detail.variant_id)
    message = TourDetailSuccess.CREATED if existing_detail is None else TourDetailSuccess.UPDATED
    return SuccessResponse(
        message=message,
        data=AdminTourService._detail_to_response(detail, variant.package_id, departures),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ActionResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Create tour variant details",
)
async def create_admin_tour_detail(
    payload: TourDetailCreateRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    await AdminTourService(db).create_detail(payload.model_dump())
    return ActionResponse(message=TourDetailSuccess.CREATED)


@router.patch(
    "/{detail_id}",
    response_model=SuccessResponse[AdminTourDetailPayload],
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Update tour variant details",
)
async def update_admin_tour_detail(
    detail_id: uuid.UUID,
    payload: TourDetailUpdateRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    detail = await service.update_detail(detail_id, payload.model_dump(exclude_unset=True))
    variant = service.get_variant(detail.variant_id)
    departures = service.get_variant_departures(detail.variant_id)
    return SuccessResponse(
        message=TourDetailSuccess.UPDATED,
        data=AdminTourService._detail_to_response(detail, variant.package_id, departures),
    )


@router.delete(
    "/{detail_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Delete tour variant details",
)
def delete_admin_tour_detail(
    detail_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).delete_detail(detail_id)
    return ActionResponse(message=TourDetailSuccess.DELETED)
