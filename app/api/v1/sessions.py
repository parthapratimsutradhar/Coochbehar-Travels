import uuid
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import (
    clear_refresh_cookie,
    extract_refresh_token,
    get_current_actor,
    set_refresh_cookie,
)
from app.core.config import settings
from app.db.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.auth import (
    AuthSessionResponse,
    MessageResponse,
    RefreshResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/sessions",
    tags=["Session Management"],
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
        clear_refresh_cookie(response)
        raise

    set_refresh_cookie(response, new_raw_refresh_token)

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
    clear_refresh_cookie(response)
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

    clear_refresh_cookie(response)
    return MessageResponse(message="Successfully logged out of all active sessions.")


@router.get(
    "/",
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
    "/{session_id}",
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
            clear_refresh_cookie(response)

    return MessageResponse(message="Session revoked successfully.")
