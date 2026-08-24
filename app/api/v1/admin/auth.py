from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, set_refresh_cookie
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AdminGoogleAuthSchema,
    AdminOtpRequestSchema,
    AdminOtpVerifySchema,
    AdminTokenResponse,
    OtpRequestResponse,
    UserResponse,
)
from app.schemas.response import SuccessResponse, ActionResponse, ErrorResponse
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/admin/auth",
    tags=["Admin - Authentication"],
)


@router.post(
    "/otp/request",
    response_model=SuccessResponse[OtpRequestResponse],
    responses={422: {"model": ErrorResponse}},
    summary="Request Admin OTP",
    description="Generate and dispatch a passwordless 6-digit OTP to the registered admin/staff email or mobile.",
)
def request_admin_otp(
    payload: AdminOtpRequestSchema,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    message, identifier, id_type, expires_in_sec, raw_otp = auth_service.request_admin_otp(
        identifier=payload.identifier,
        purpose=payload.purpose,
    )
    return SuccessResponse(
        message=message,
        data=OtpRequestResponse(
            identifier=identifier,
            identifier_type=id_type,
            expires_in_sec=expires_in_sec,
            dev_otp=raw_otp,
        ),
    )


@router.post(
    "/otp/verify",
    response_model=SuccessResponse[AdminTokenResponse],
    responses={422: {"model": ErrorResponse}},
    summary="Verify Admin OTP & Login",
    description="Verify the 6-digit OTP, create a 30-day refresh session, set HttpOnly cookie, and return a 15-minute access JWT.",
)
def verify_admin_otp(
    payload: AdminOtpVerifySchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = AuthService(db)
    access_token, raw_refresh_token = auth_service.verify_admin_otp(
        identifier=payload.identifier,
        otp=payload.otp,
        purpose=payload.purpose,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    set_refresh_cookie(response, raw_refresh_token)

    return SuccessResponse(
        message="Admin authenticated successfully.",
        data=AdminTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=raw_refresh_token,
        ),
    )


@router.post(
    "/google",
    response_model=SuccessResponse[AdminTokenResponse],
    responses={422: {"model": ErrorResponse}},
    summary="Admin Continue with Google",
    description="Authenticate an active Admin account via Google OAuth ID token.",
)
async def google_login_admin(
    payload: AdminGoogleAuthSchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = AuthService(db)
    access_token, raw_refresh_token = await auth_service.google_login_admin(
        id_token=payload.id_token,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    set_refresh_cookie(response, raw_refresh_token)

    return SuccessResponse(
        message="Admin authenticated successfully with Google.",
        data=AdminTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=raw_refresh_token,
        ),
    )


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Get Authenticated Admin Profile",
)
def get_current_admin_profile(
    current_user: User = Depends(get_current_user),
):
    return SuccessResponse(
        message="Admin profile fetched successfully.",
        data=UserResponse.model_validate(current_user),
    )

