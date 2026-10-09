import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.core.enums import PointTransactionType, TourType
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.schemas.tour_points import (
    AdminTourPointTransactionResponse,
    AdminUserRankingItem,
    TourPointConfigurationHistoryResponse,
    TourPointConfigurationResponse,
    TourPointConfigurationUpdate,
)
from app.services.tour_points_service import TourPointsService
from app.utils.cdn_urls import cdn_url_for_value

router = APIRouter(prefix="/admin/points", tags=["Admin - Tour Points"])


@router.get(
    "/config",
    response_model=SuccessResponse[list[TourPointConfigurationResponse]],
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Get domestic and international point rates",
    description=(
        "Returns the current persisted points configuration for each tour category. "
        "The amount_per_point value is the INR price required to earn one point."
    ),
    response_description="Current domestic and international point rates.",
)
def get_point_configurations(
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    return SuccessResponse(
        message="Tour point configurations fetched successfully",
        data=[TourPointConfigurationResponse.model_validate(item) for item in TourPointsService(db).get_configurations()],
    )


@router.get(
    "/config/history",
    response_model=SuccessResponse[list[TourPointConfigurationHistoryResponse]],
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="List point-rate configuration changes",
    description=(
        "Returns up to the 200 most recent immutable configuration changes. "
        "Use tour_type to limit results to DOMESTIC or INTERNATIONAL."
    ),
    response_description="Configuration change history, newest first.",
)
def get_point_configuration_history(
    tour_type: TourType | None = Query(
        default=None,
        description="Optional tour category filter.",
        examples=["DOMESTIC"],
    ),
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    rows = TourPointsService(db).get_configuration_history(tour_type)
    return SuccessResponse(
        message="Tour point configuration history fetched successfully",
        data=[
            TourPointConfigurationHistoryResponse(
                id=item.id,
                configuration_id=item.configuration_id,
                tour_type=item.tour_type,
                previous_amount_per_point=item.previous_amount_per_point,
                amount_per_point=item.amount_per_point,
                changed_by_account_id=item.changed_by_account_id,
                changed_by_account_profile_pic=(
                    cdn_url_for_value(item.changed_by_account.profile_pic)
                    if item.changed_by_account and item.changed_by_account.profile_pic
                    else None
                ),
                changed_by_account_name=(
                    item.changed_by_account.name
                    if item.changed_by_account
                    else "System" if item.previous_amount_per_point is None else None
                ),
                changed_by_account_email=(
                    item.changed_by_account.email if item.changed_by_account else None
                ),
                changed_by_account_mobile=(
                    item.changed_by_account.mobile if item.changed_by_account else None
                ),
                changed_at=item.changed_at,
            )
            for item in rows
        ],
    )


@router.put(
    "/config/{tour_type}",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Update the points rate for a tour category",
    description=(
        "Sets the INR amount required to earn one point for the selected tour category. "
        "The change is persisted and appended to configuration history; prior bookings retain their original rate snapshot."
    ),
    response_description="Confirmation that the configuration was updated.",
)
def update_point_configuration(
    tour_type: Annotated[
        TourType,
        Path(description="Tour category to update: DOMESTIC or INTERNATIONAL."),
    ],
    payload: TourPointConfigurationUpdate,
    current_admin: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    TourPointsService(db).update_configuration(tour_type, payload.amount_per_point, current_admin.id)
    return ActionResponse(message="Tour point configuration updated successfully")


@router.get(
    "/transactions",
    response_model=PaginatedResponse[AdminTourPointTransactionResponse],
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Search and filter point transactions",
    description=(
        "Returns an audit-friendly, newest-first page of point transactions. Points are signed: "
        "booking awards are positive and cancellation reversals are negative. Filters can be combined. "
        "search matches customer name/email/account code, booking code, or tour title."
    ),
    response_description="A page of point transactions with pagination metadata.",
)
def list_point_transactions(
    page: int = Query(1, ge=1, description="One-based result page."),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page (maximum 100)."),
    account_id: uuid.UUID | None = Query(None, description="Filter to one customer account ID."),
    booking_id: uuid.UUID | None = Query(None, description="Filter to one booking ID."),
    package_id: uuid.UUID | None = Query(None, description="Filter to one tour package ID."),
    transaction_type: PointTransactionType | None = Query(
        None,
        description="Filter by BOOKING_EARNED, BOOKING_REVERSED, or MANUAL_ADJUSTMENT.",
    ),
    created_from: datetime | None = Query(None, description="Inclusive lower transaction timestamp; accepts ISO 8601."),
    created_to: datetime | None = Query(None, description="Inclusive upper transaction timestamp; accepts ISO 8601."),
    points_min: Decimal | None = Query(None, description="Minimum signed point delta, including negative reversals."),
    points_max: Decimal | None = Query(None, description="Maximum signed point delta, including negative reversals."),
    search: str | None = Query(
        None,
        max_length=200,
        description="Search customer name/email/account code, booking code, or tour title.",
    ),
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    rows, total = TourPointsService(db).list_transactions(
        page=page,
        page_size=page_size,
        account_id=account_id,
        booking_id=booking_id,
        package_id=package_id,
        transaction_type=transaction_type,
        created_from=created_from,
        created_to=created_to,
        points_min=points_min,
        points_max=points_max,
        search=search,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(
        message="Tour point transactions fetched successfully",
        data=[AdminTourPointTransactionResponse(
            id=row.id,
            booking_id=row.booking_id,
            package_id=row.package_id,
            booking_code=row.booking_code,
            tour_title=row.tour_title,
            transaction_type=row.transaction_type,
            points=row.points,
            balance_before=row.balance_before,
            balance_after=row.balance_after,
            amount_per_point=row.amount_per_point,
            reason=row.reason,
            created_at=row.created_at,
            customer_id=row.account_id,
            customer_code=row.account.account_code,
            customer_name=row.account.name,
            customer_email=row.account.email,
            customer_mobile=row.account.mobile,
            customer_profile_pic=(
                cdn_url_for_value(row.account.profile_pic) if row.account.profile_pic else None
            ),
        ) for row in rows],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.get(
    "/rankings",
    response_model=PaginatedResponse[AdminUserRankingItem],
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="List customer rankings by current point balance",
    description=(
        "Returns active customer accounts ranked by their latest persisted point balance, highest first. "
        "Ties are resolved deterministically by account ID."
    ),
    response_description="A page of ranked customers with pagination metadata.",
)
def list_user_rankings(
    page: int = Query(1, ge=1, description="One-based result page."),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page (maximum 100)."),
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    rows, total = TourPointsService(db).list_rankings(page=page, page_size=page_size, include_spend=True)
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(
        message="User rankings fetched successfully",
        data=[AdminUserRankingItem(
            rank=row.rank,
            customer_id=row.account_id,
            customer_code=row.account_code,
            customer_name=row.name,
            customer_profile_picture=cdn_url_for_value(row.profile_pic) if row.profile_pic else None,
            points=row.points,
            customer_joined_at=row.customer_joined_at,
            money_spends=Decimal(row.money_spends).quantize(Decimal("0.01")),
        ) for row in rows],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )
