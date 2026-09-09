import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only, get_current_user
from app.core.enums import AccountRole
from app.core.messages.error import AccessError, UserError
from app.core.messages.success import UserSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.account import AdminDeleteProfileRequest, AdminProfileUpdate
from app.schemas.auth import UserResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.services.auth_service import AuthService


router = APIRouter(
	prefix="/admin/account",
	tags=["Admin - Account Management"],
)


def _ensure_update_permission(current_user: Account, account: Account) -> None:
	if current_user.role == AccountRole.ADMIN:
		if account.role == AccountRole.ADMIN and account.id != current_user.id:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)
		return

	if current_user.role == AccountRole.STAFF:
		if account.id != current_user.id or account.role == AccountRole.ADMIN:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)
		return

	raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)


def _ensure_delete_permission(current_user: Account, account: Account) -> None:
	if current_user.role == AccountRole.ADMIN:
		if account.role == AccountRole.ADMIN and account.id != current_user.id:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)
		return

	raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)


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
	stmt = select(Account).where(
		Account.role.in_((AccountRole.ADMIN, AccountRole.STAFF)),
		Account.id != current_admin.id,
	)
	if search:
		term = f"%{search.strip()}%"
		stmt = stmt.where(
			Account.name.ilike(term)
			| Account.email.ilike(term)
			| Account.mobile.ilike(term)
		)
	if role:
		stmt = stmt.where(Account.role == role)
	if is_active is not None:
		stmt = stmt.where(Account.is_active == is_active)

	total_items = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
	accounts = db.execute(
		stmt.order_by(Account.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
	).scalars().all()
	total_pages = (total_items + page_size - 1) // page_size
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
def update_account(
	user_id: uuid.UUID,
	payload: AdminProfileUpdate,
	current_user: Account = Depends(get_current_user),
	db: Session = Depends(get_db),
):
	account = db.execute(select(Account).where(Account.id == user_id)).scalar_one_or_none()
	if not account or account.role not in (AccountRole.ADMIN, AccountRole.STAFF):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=UserError.USER_NOT_FOUND)

	_ensure_update_permission(current_user, account)

	target_role = payload.role or account.role
	if payload.email and db.execute(select(Account).where(
		Account.email == payload.email.strip().lower(),
		Account.role == target_role,
		Account.id != user_id,
	)).scalar_one_or_none():
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.EMAIL_ALREADY_EXISTS)
	if payload.mobile and db.execute(select(Account).where(
		Account.mobile == payload.mobile.strip(),
		Account.role == target_role,
		Account.id != user_id,
	)).scalar_one_or_none():
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.MOBILE_ALREADY_EXISTS)

	update_data = payload.model_dump(exclude_unset=True)
	if "email" in update_data:
		update_data["email"] = update_data["email"].strip().lower()
	if "mobile" in update_data:
		update_data["mobile"] = update_data["mobile"].strip()
	for field, value in update_data.items():
		setattr(account, field, value)
	try:
		db.commit()
	except IntegrityError:
		db.rollback()
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.CONTACT_ALREADY_EXISTS)
	db.refresh(account)
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
	account = db.execute(select(Account).where(Account.id == user_id)).scalar_one_or_none()
	if not account or account.role not in (AccountRole.ADMIN, AccountRole.STAFF):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=UserError.USER_NOT_FOUND)

	# strict role policy:
	# 1. admin may delete any staff account, but cannot delete another admin
	# 2. staff may not delete any account
	if current_user.role == AccountRole.ADMIN:
		if account.role == AccountRole.ADMIN and account.id != current_user.id:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)
	elif current_user.role == AccountRole.STAFF:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)
	else:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)

	# OTP must be verified for the acting admin identity, matching the provided identifier
	if payload.identifier.strip().lower() != current_user.email.lower() and payload.identifier.strip() != current_user.mobile:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.OTP_ADMIN_REQUIRED)

	AuthService(db).verify_admin_otp_for_action(
		identifier=payload.identifier,
		otp=payload.otp,
		purpose="DELETE_ACCOUNT",
	)
	account.is_active = False
	db.commit()
	return ActionResponse(message=UserSuccess.DELETED)
