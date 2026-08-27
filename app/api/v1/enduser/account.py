from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.api.deps import clear_refresh_cookie, get_current_customer
from app.db.database import get_db
from app.models.customer import Customer
from app.schemas.auth import CustomerOtpVerifySchema
from app.schemas.customer import CustomerResponse, CustomerUpdate
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/account",
    tags=["Enduser - Customer Account Management"],
)


@router.get(
    "/me",
    response_model=SuccessResponse[CustomerResponse],
    summary="Get Authenticated Customer Profile",
)
def get_current_customer_profile(
    current_customer: Customer = Depends(get_current_customer),
):
    return SuccessResponse(
        message="Customer profile fetched successfully.",
        data=CustomerResponse.model_validate(current_customer),
    )


@router.patch(
    "/me",
    response_model=SuccessResponse[CustomerResponse],
    responses={422: {"model": ErrorResponse}},
    summary="Update Customer Profile",
)
def update_customer_profile(
    payload: CustomerUpdate,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    updated = auth_service.customer_repo.update_customer(
        customer=current_customer,
        update_data=payload.model_dump(exclude_unset=True),
    )
    return SuccessResponse(
        message="Customer profile updated successfully.",
        data=CustomerResponse.model_validate(updated),
    )


@router.delete(
    "/me",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
    summary="Delete Customer Account",
    description="Verify a DELETE_ACCOUNT OTP for the authenticated customer's email or mobile number, then permanently delete the account.",
)
def delete_customer_account(
    payload: CustomerOtpVerifySchema,
    response: Response,
    current_customer: Customer = Depends(get_current_customer),
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
    return ActionResponse(message="Customer account deleted successfully.")
