import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only, get_current_user
from app.core.enums import AccountRole
from app.core.messages.success import UserSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.account import AdminDeleteProfileRequest, AdminProfileUpdate, AdminStaffCreate
from app.schemas.auth import UserResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.services.account_service import AdminAccountService


router = APIRouter(
    prefix="/admin/account",
    tags=["Admin - Account Management"],
)


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Create a staff account",
)
async def create_staff(
    payload: AdminStaffCreate,
    current_admin: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    await AdminAccountService(db).create_staff(payload)
    return ActionResponse(message=UserSuccess.CREATED)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="List admin and staff accounts",
)
def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search across email, name, and mobile"),
    role: AccountRole | None = Query(None),
    is_active: bool | None = Query(None),
    current_admin: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    accounts, total_items, total_pages = AdminAccountService(db).list_accounts(
        current_admin=current_admin,
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        is_active=is_active,
    )
    return PaginatedResponse[UserResponse](
        message=UserSuccess.RETRIEVED,
        data=[UserResponse.model_validate(account) for account in accounts],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.patch(
    "/{user_id}",
    response_model=ActionResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Update an admin or staff profile",
)
async def update_account(
    user_id: uuid.UUID,
    payload: AdminProfileUpdate,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    await AdminAccountService(db).update_account(current_user=current_user, user_id=user_id, payload=payload)
    return ActionResponse(message=UserSuccess.UPDATED)


@router.delete(
    "/{user_id}",
    response_model=ActionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Delete an admin or staff profile",
)
def delete_account(
    user_id: uuid.UUID,
    payload: AdminDeleteProfileRequest,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AdminAccountService(db).delete_account(current_user=current_user, user_id=user_id, payload=payload)
    return ActionResponse(message=UserSuccess.DELETED)
