from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer, set_refresh_cookie
from app.core.config import settings
from app.db.database import get_db
from app.models.customer import Customer
from app.schemas.auth import (
    CustomerGoogleAuthSchema,
    CustomerOtpRequestSchema,
    CustomerOtpVerifySchema,
    CustomerTokenResponse,
    OtpRequestResponse,
)
from app.schemas.customer import CustomerResponse, CustomerUpdate
from app.schemas.response import SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/enduser/auth",
    tags=["Enduser - Customer Authentication"],
)


@router.post(
    "/otp/request",
    response_model=SuccessResponse[OtpRequestResponse],
    summary="Request Customer Login / Register OTP",
    description="Dispatch a passwordless 6-digit OTP to a traveler's mobile number or email.",
)
def request_customer_otp(
    payload: CustomerOtpRequestSchema,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    message, identifier, id_type, expires_in, raw_otp = auth_service.request_customer_otp(
        identifier=payload.identifier,
        purpose=payload.purpose,
        visitor_id=payload.visitor_id,
    )
    return SuccessResponse(
        message=message,
        data=OtpRequestResponse(
            identifier=identifier,
            identifier_type=id_type,
            expires_in_sec=expires_in,
            dev_otp=raw_otp,
        ),
    )


@router.post(
    "/otp/verify",
    response_model=SuccessResponse[CustomerTokenResponse],
    summary="Verify Customer OTP, Auto-Register & Link Visitor",
    description="Verifies the OTP, auto-creates a customer profile if first-time traveler, links web visitor telemetry, creates a 30-day session, and returns a 15-minute access JWT.",
)
def verify_customer_otp(
    payload: CustomerOtpVerifySchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = AuthService(db)
    access_token, raw_refresh_token, customer = auth_service.verify_customer_otp(
        identifier=payload.identifier,
        otp=payload.otp,
        name=payload.name,
        purpose=payload.purpose,
        visitor_id=payload.visitor_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    set_refresh_cookie(response, raw_refresh_token)

    return SuccessResponse(
        message="Customer authenticated successfully.",
        data=CustomerTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            customer=CustomerResponse.model_validate(customer),
        ),
    )


@router.post(
    "/google",
    response_model=SuccessResponse[CustomerTokenResponse],
    summary="Customer Continue with Google",
    description="Authenticate or auto-register a traveler via Google OAuth ID token and automatically link web visitor telemetry.",
)
def google_login_customer(
    payload: CustomerGoogleAuthSchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = AuthService(db)
    access_token, raw_refresh_token, customer = auth_service.google_login_customer(
        id_token=payload.id_token,
        visitor_id=payload.visitor_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    set_refresh_cookie(response, raw_refresh_token)

    return SuccessResponse(
        message="Customer authenticated successfully with Google.",
        data=CustomerTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            customer=CustomerResponse.model_validate(customer),
        ),
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


@router.put(
    "/me",
    response_model=SuccessResponse[CustomerResponse],
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

