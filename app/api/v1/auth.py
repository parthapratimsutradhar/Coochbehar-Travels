import uuid
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import extract_refresh_token, get_current_actor
from app.core.config import settings
from app.db.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.auth import (
    AdminTokenResponse,
    AuthSessionResponse,
    CustomerTokenResponse,
    GoogleAuthSchema,
    MessageResponse,
    OtpRequestResponse,
    OtpRequestSchema,
    OtpVerifySchema,
    RefreshResponse,
    UserResponse,
)
from app.schemas.customer import CustomerResponse
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication & Sessions"],
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


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )
    response.delete_cookie(key="refresh_token", path="/")
    response.delete_cookie(key="__Host-refresh_token", path="/")


@router.post(
    "/otp/request",
    response_model=OtpRequestResponse,
    summary="Request Customer OTP",
    description="Convenience route to request an OTP for customer login/registration.",
)
def request_otp(
    payload: OtpRequestSchema,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    message, identifier, id_type, expires_in, raw_otp = auth_service.request_customer_otp(
        identifier=payload.identifier,
        identifier_type=payload.identifier_type,
        purpose=payload.purpose,
        visitor_id=payload.visitor_id,
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
    response_model=CustomerTokenResponse,
    summary="Verify Customer OTP",
    description="Convenience route to verify customer OTP and obtain tokens.",
)
def verify_otp(
    payload: OtpVerifySchema,
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

    _set_refresh_cookie(response, raw_refresh_token)

    return CustomerTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        customer=CustomerResponse.model_validate(customer),
    )


@router.post(
    "/google",
    response_model=CustomerTokenResponse,
    summary="Customer Continue with Google",
    description="Authenticate or auto-register a traveler via Google OAuth ID token.",
)
def google_login(
    payload: GoogleAuthSchema,
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

    _set_refresh_cookie(response, raw_refresh_token)

    return CustomerTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        customer=CustomerResponse.model_validate(customer),
    )


@router.post(
    "/admin/google",
    response_model=AdminTokenResponse,
    summary="Admin Continue with Google",
    description="Authenticate an Admin account via Google OAuth ID token.",
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


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Renew Access Token",
    description="Rotates the refresh token from the HttpOnly cookie, preserves original 30-day max expiration, and returns a new 15-minute access JWT.",
)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_refresh_token = extract_refresh_token(request)
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = AuthService(db)
    try:
        new_access_token, new_raw_refresh_token = auth_service.refresh_session(
            raw_refresh_token=raw_refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    except Exception:
        _clear_refresh_cookie(response)
        raise

    _set_refresh_cookie(response, new_raw_refresh_token)

    return RefreshResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout current session",
    description="Revokes the current refresh session and clears the HttpOnly refresh token cookie.",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_refresh_token = extract_refresh_token(request)
    auth_service = AuthService(db)
    auth_service.logout(raw_refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Successfully logged out.")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Logout all active sessions",
    description="Revokes all active sessions for the authenticated actor (User or Customer) and clears the refresh cookie.",
)
def logout_all(
    response: Response,
    actor_info: tuple[User | Customer, str] = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    actor, actor_type = actor_info
    auth_service = AuthService(db)
    if actor_type == "USER":
        auth_service.logout_all_for_actor(user_id=actor.id)
    else:
        auth_service.logout_all_for_actor(customer_id=actor.id)

    _clear_refresh_cookie(response)
    return MessageResponse(message="Successfully logged out of all active sessions.")


@router.get(
    "/sessions",
    response_model=list[AuthSessionResponse],
    summary="List active sessions",
    description="Retrieve all non-revoked sessions for the authenticated actor (User or Customer).",
)
def list_sessions(
    request: Request,
    actor_info: tuple[User | Customer, str] = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    actor, actor_type = actor_info
    current_refresh_token = extract_refresh_token(request)
    auth_service = AuthService(db)

    if actor_type == "USER":
        return auth_service.get_actor_sessions(
            user_id=actor.id,
            current_refresh_token=current_refresh_token,
        )
    else:
        return auth_service.get_actor_sessions(
            customer_id=actor.id,
            current_refresh_token=current_refresh_token,
        )


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
    summary="Revoke a specific session",
    description="Revoke an individual session belonging to the authenticated actor.",
)
def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    response: Response,
    actor_info: tuple[User | Customer, str] = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    actor, actor_type = actor_info
    auth_service = AuthService(db)

    if actor_type == "USER":
        auth_service.revoke_session_by_id(session_id=session_id, user_id=actor.id)
    else:
        auth_service.revoke_session_by_id(session_id=session_id, customer_id=actor.id)

    current_refresh_token = extract_refresh_token(request)
    if current_refresh_token:
        session = auth_service.session_repo.get_by_id(session_id)
        if session and session.revoked_at is not None:
            _clear_refresh_cookie(response)

    return MessageResponse(message="Session revoked successfully.")
