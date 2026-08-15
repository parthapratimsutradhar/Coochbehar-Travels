from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AdminTokenResponse,
    GoogleAuthSchema,
    OtpRequestResponse,
    OtpRequestSchema,
    OtpVerifySchema,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/admin/auth",
    tags=["Admin - Authentication"],
)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        expires=max_age,
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


@router.post(
    "/otp/request",
    response_model=OtpRequestResponse,
    summary="Request Admin OTP",
    description="Generate and dispatch a passwordless 6-digit OTP to the registered admin/staff email or mobile.",
)
def request_admin_otp(
    payload: OtpRequestSchema,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    message, identifier, id_type, expires_in, raw_otp = auth_service.request_admin_otp(
        identifier=payload.identifier,
        purpose=payload.purpose,
    )
    return OtpRequestResponse(
        message=message,
        identifier=identifier,
        identifier_type=id_type,
        expires_in=expires_in,
        dev_otp=raw_otp,
    )


@router.post(
    "/otp/verify",
    response_model=AdminTokenResponse,
    summary="Verify Admin OTP & Login",
    description="Verify the 6-digit OTP, create a 30-day refresh session, set HttpOnly cookie, and return a 15-minute access JWT.",
)
def verify_admin_otp(
    payload: OtpVerifySchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = AuthService(db)
    access_token, raw_refresh_token, user = auth_service.verify_admin_otp(
        identifier=payload.identifier,
        otp=payload.otp,
        purpose=payload.purpose,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    _set_refresh_cookie(response, raw_refresh_token)

    return AdminTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/google",
    response_model=AdminTokenResponse,
    summary="Admin Continue with Google",
    description="Authenticate an active Admin account via Google OAuth ID token.",
)
def google_login_admin(
    payload: GoogleAuthSchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = AuthService(db)
    access_token, raw_refresh_token, user = auth_service.google_login_admin(
        id_token=payload.id_token,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    _set_refresh_cookie(response, raw_refresh_token)

    return AdminTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Authenticated Admin Profile",
)
def get_current_admin_profile(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)
