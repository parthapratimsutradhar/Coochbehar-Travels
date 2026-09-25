import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.core.enums import ReferralStatus
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.referral import (
    ReferralListItemResponse,
    ReferralManualUpdateRequest,
    ReferralRewardConfigRequest,
    ReferralRewardConfigResponse,
)
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/admin/referrals", tags=["Admin - Referrals"])


@router.get(
    "/config",
    response_model=SuccessResponse[ReferralRewardConfigResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Get the default referral reward configuration",
)
def get_referral_config(
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = ReferralService(db)
    return SuccessResponse(
        message="Referral reward configuration fetched successfully",
        data=service.get_referral_config(),
    )


@router.patch(
    "/config",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Update the default referral reward configuration",
)
def update_referral_config(
    payload: ReferralRewardConfigRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    service = ReferralService(db)
    service.update_referral_config(payload=payload, current_user=current_user)
    return ActionResponse(message="Referral reward configuration updated successfully")


@router.get(
    "",
    response_model=PaginatedResponse[ReferralListItemResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="List all referrals",
)
def list_referrals(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: ReferralStatus | None = Query(None),
    search: str | None = Query(None),
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = ReferralService(db)
    referrals, total_items = service.list_referrals(
        page=page,
        page_size=page_size,
        status=status,
        search=search,
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0

    return PaginatedResponse(
        message="Items fetched successfully",
        data=referrals,
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.patch(
    "/{referral_id}",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Manually update referral status or reward amount",
)
def update_referral(
    referral_id: uuid.UUID,
    payload: ReferralManualUpdateRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    service = ReferralService(db)
    service.update_referral(
        referral_id=referral_id,
        payload=payload,
        current_user=current_user,
    )
    return ActionResponse(message="Referral updated successfully")
