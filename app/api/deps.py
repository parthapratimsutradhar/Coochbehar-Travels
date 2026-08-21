import uuid
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import UserRole
from app.core.messages.validation import AuthError
from app.db.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.repository.customer_repo import CustomerRepository
from app.repository.user_repo import UserRepository
from app.utils.security import decode_access_token

security_bearer = HTTPBearer(auto_error=False)


def _get_token_payload(credentials: HTTPAuthorizationCredentials | None) -> dict:
    """Helper to extract and validate token payload."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AuthError.UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_admin_or_staff(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT access token for an Admin / Staff user."""
    payload = _get_token_payload(credentials)
    actor_type = payload.get("actor_type")

    if actor_type not in ["ADMIN", "STAFF"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin/Staff access required.",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject missing.",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token.",
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    return user


get_current_user = get_current_admin_or_staff


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure authenticated user has ADMIN or STAFF role."""
    if current_user.role not in (UserRole.ADMIN, UserRole.STAFF):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=AuthError.ACCESS_DENIED,
        )
    return current_user


def get_current_admin_only(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure authenticated user has the ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return current_user


def get_current_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> Customer:
    """Extract and validate JWT access token for an Enduser / Customer."""
    payload = _get_token_payload(credentials)
    actor_type = payload.get("actor_type", "CUSTOMER")

    if actor_type != "CUSTOMER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required.",
        )

    customer_id_str = payload.get("sub")
    if not customer_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject missing.",
        )

    try:
        customer_id = uuid.UUID(customer_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer ID in token.",
        )

    customer_repo = CustomerRepository(db)
    customer = customer_repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer profile not found.",
        )

    return customer


def get_current_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> tuple[User | Customer, str]:
    """Universal actor resolver: returns (User or Customer, actor_type)."""
    payload = _get_token_payload(credentials)
    actor_type = payload.get("actor_type")
    sub = payload.get("sub")
    if not actor_type or not sub:
        raise HTTPException(status_code=401, detail="Invalid token claims.")

    try:
        sub_id = uuid.UUID(sub)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid actor ID in token.")

    if actor_type in ("ADMIN", "STAFF"):
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(sub_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User inactive or not found.")
        return user, actor_type

    if actor_type == "CUSTOMER":
        customer_repo = CustomerRepository(db)
        customer = customer_repo.get_by_id(sub_id)
        if not customer:
            raise HTTPException(status_code=401, detail="Customer not found.")
        return customer, "CUSTOMER"

    raise HTTPException(status_code=401, detail="Invalid actor type in token.")


def get_current_access_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> dict:
    """Return the validated access-token claims for session-aware endpoints."""
    return _get_token_payload(credentials)


def extract_refresh_token(request: Request) -> str | None:
    """Extract refresh token from HttpOnly cookie with fallback support."""
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if token:
        return token
    return (
        request.cookies.get("refresh_token")
        or request.cookies.get("__Host-refresh_token")
    )


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set the HttpOnly refresh-token cookie with consistent settings."""
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


def clear_refresh_cookie(response: Response) -> None:
    """Delete all possible refresh-token cookies."""
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )
    response.delete_cookie(key="refresh_token", path="/")
    response.delete_cookie(key="__Host-refresh_token", path="/")
