import math
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.api.deps import clear_refresh_cookie, get_current_customer
from app.db.database import get_db
from app.models.account import Account
from app.schemas.auth import CustomerOtpVerifySchema
from app.schemas.customer import CustomerResponse, CustomerUpdate
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.schemas.pagination import PaginationMeta
from app.schemas.tour_points import (
    CustomerPointsResponse,
    CustomerRankPositionResponse,
    TourPointTransactionResponse,
)
from app.services.auth_service import AuthService
from app.services.customer_service import CustomerService
from app.services.tour_points_service import DEFAULT_RANKING_PAGE_SIZE, TourPointsService

router = APIRouter(
    prefix="/account",
    tags=["Enduser - Customer Account Management"],
)


@router.get("/points", response_model=SuccessResponse[CustomerPointsResponse])
def get_customer_points(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = TourPointsService(db)
    ranking = service.get_customer_ranking(current_customer.id)
    transactions, total = service.list_transactions(
        page=page,
        page_size=page_size,
        account_id=current_customer.id,
    )
    total_pages = math.ceil(total / page_size) if total else 0
    return SuccessResponse(
        message="Points, ranking, and transaction history fetched successfully",
        data=CustomerPointsResponse(
            points_balance=ranking["current"].points,
            rank=ranking["current"].rank,
            transactions=[TourPointTransactionResponse.model_validate(row) for row in transactions],
            transaction_pagination=PaginationMeta(
                current_page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        ),
    )


@router.get(
    "/points/rank-position",
    response_model=SuccessResponse[CustomerRankPositionResponse],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Get the authenticated customer's leaderboard position",
    description="Returns the customer's current rank and one-based page number for the 10-entry public leaderboard pages.",
)
def get_customer_rank_position(
    page_size: int = Query(DEFAULT_RANKING_PAGE_SIZE, ge=1, le=100),
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    position = TourPointsService(db).get_customer_rank_position(current_customer.id, page_size)
    return SuccessResponse(
        message="Your current ranking position fetched successfully",
        data=CustomerRankPositionResponse(**position),
    )


@router.patch(
    "/me",
    response_model=SuccessResponse[CustomerResponse],
    responses={422: {"model": ErrorResponse}},
    summary="Update Customer Profile",
)
async def update_customer_profile(
    payload: CustomerUpdate,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    updated = await CustomerService(db).update_customer(current_customer.id, payload)
    return SuccessResponse(
        message="Customer profile updated successfully.",
        data=updated,
    )


@router.delete(
    "/me",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
    summary="Delete Customer Account",
    description="Verify a DELETE_ACCOUNT OTP for the authenticated customer's email or mobile number, then deactivate the account.",
)
def delete_customer_account(
    payload: CustomerOtpVerifySchema,
    response: Response,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    auth_service.verify_customer_otp_for_action(
        customer=current_customer,
        identifier=payload.identifier,
        otp=payload.otp,
        purpose="DELETE_ACCOUNT",
    )
    auth_service.customer_repo.delete_customer(current_customer)
    clear_refresh_cookie(response)
    return ActionResponse(message="Customer account deactivated successfully.")
