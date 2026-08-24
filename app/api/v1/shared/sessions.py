import uuid
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import (
    clear_refresh_cookie,
    extract_refresh_token,
    get_current_access_token_payload,
    get_current_actor,
    set_refresh_cookie,
)
from app.core.config import settings
from app.db.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.auth import (
    AuthSessionResponse,
    RefreshResponse,
    RefreshSessionRequest,
)
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/sessions",
    tags=["Session Management"],
)


@router.post(
    "/refresh",
    response_model=SuccessResponse[RefreshResponse],
    summary="Renew Access Token",
    description="Rotates the refresh token from HttpOnly cookie or payload/header fallback, preserves original 30-day max expiration, and returns a new 15-minute access JWT.",
)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshSessionRequest | None = None,
    db: Session = Depends(get_db),
):
    raw_refresh_token = (
        (payload.refresh_token.strip() if payload and payload.refresh_token else None)
        or extract_refresh_token(request)
    )
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = AuthService(db)
    try:
        new_access_token, new_raw_refresh_token, absolute_expires_at = auth_service.refresh_session(
            raw_refresh_token=raw_refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    except Exception:
        clear_refresh_cookie(response)
        raise

    set_refresh_cookie(response, new_raw_refresh_token, absolute_expires_at)

    return SuccessResponse(
        message="Token refreshed successfully.",
        data=RefreshResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=new_raw_refresh_token,
        ),
    )


@router.post(
    "/logout",
    response_model=ActionResponse,
    summary="Logout current session",
    description="Revokes the current refresh session and clears the HttpOnly refresh token cookie.",
)
def logout(
    request: Request,
    response: Response,
    payload: RefreshSessionRequest | None = None,
    db: Session = Depends(get_db),
):
    raw_refresh_token = (
        (payload.refresh_token.strip() if payload and payload.refresh_token else None)
        or extract_refresh_token(request)
    )
    auth_service = AuthService(db)
    auth_service.logout(raw_refresh_token)
    clear_refresh_cookie(response)
    return ActionResponse(message="Successfully logged out.")


@router.post(
    "/logout-all",
    response_model=ActionResponse,
    summary="Logout all active sessions",
    description="Revokes all active sessions for the authenticated actor (User or Customer) and clears the refresh cookie.",
)
def logout_all(
    response: Response,
    access_token_payload: dict = Depends(get_current_access_token_payload),
    actor_info: tuple[User | Customer, str] = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    actor, actor_type = actor_info
    current_session_id = None
    session_id_claim = access_token_payload.get("session_id")
    if session_id_claim:
        try:
            current_session_id = uuid.UUID(session_id_claim)
        except (ValueError, AttributeError):
            current_session_id = None

    auth_service = AuthService(db)
    if actor_type in ("ADMIN", "STAFF"):
        auth_service.logout_all_for_actor(
            user_id=actor.id,
            exclude_session_id=current_session_id,
        )
    else:
        auth_service.logout_all_for_actor(
            customer_id=actor.id,
            exclude_session_id=current_session_id,
        )

    return ActionResponse(message="Successfully logged out of all active sessions.")


@router.get(
    "/",
    response_model=SuccessResponse[list[AuthSessionResponse]],
    summary="List active sessions",
    description="Retrieve all non-revoked sessions for the authenticated actor (User or Customer).",
)
def list_sessions(
    request: Request,
    access_token_payload: dict = Depends(get_current_access_token_payload),
    actor_info: tuple[User | Customer, str] = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    actor, actor_type = actor_info
    current_refresh_token = extract_refresh_token(request)
    current_session_id = None
    session_id_claim = access_token_payload.get("session_id")
    if session_id_claim:
        try:
            current_session_id = uuid.UUID(session_id_claim)
        except (ValueError, AttributeError):
            current_session_id = None
    auth_service = AuthService(db)

    if actor_type in ("ADMIN", "STAFF"):
        sessions = auth_service.get_actor_sessions(
            user_id=actor.id,
            current_refresh_token=current_refresh_token,
            current_session_id=current_session_id,
        )
    else:
        sessions = auth_service.get_actor_sessions(
            customer_id=actor.id,
            current_refresh_token=current_refresh_token,
            current_session_id=current_session_id,
        )
    return SuccessResponse(
        message="Active sessions retrieved successfully.",
        data=sessions,
    )


@router.delete(
    "/{session_id}",
    response_model=ActionResponse,
    responses={422: {"model": ErrorResponse}},
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

    if actor_type in ("ADMIN", "STAFF"):
        auth_service.revoke_session_by_id(session_id=session_id, user_id=actor.id)
    else:
        auth_service.revoke_session_by_id(session_id=session_id, customer_id=actor.id)

    current_refresh_token = extract_refresh_token(request)
    if current_refresh_token:
        session = auth_service.session_repo.get_by_id(session_id)
        if session and session.revoked_at is not None:
            clear_refresh_cookie(response)

    return ActionResponse(message="Session revoked successfully.")

