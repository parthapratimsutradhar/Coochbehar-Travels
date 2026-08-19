import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.core.enums import UserRole
from app.db.database import get_db
from app.models.user import User
from app.schemas.account import AdminDeleteProfileRequest, AdminProfileUpdate
from app.schemas.auth import UserResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.services.auth_service import AuthService


router = APIRouter(
	prefix="/admin/account",
	tags=["Admin - Account Management"],
)


@router.get(
	"",
	response_model=PaginatedResponse[UserResponse],
	responses={403: {"model": ErrorResponse}},
	summary="List admin and staff accounts",
)
def list_accounts(
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	email: str | None = Query(None),
	phone: str | None = Query(None, description="Filter by phone"),
	name: str | None = Query(None),
	role: UserRole | None = Query(None),
	current_admin: User = Depends(get_current_admin_only),
	db: Session = Depends(get_db),
):
	stmt = select(User).where(User.role.in_((UserRole.ADMIN, UserRole.STAFF)))
	if email:
		stmt = stmt.where(User.email.ilike(f"%{email.strip()}%"))
	if phone:
		stmt = stmt.where(User.mobile.ilike(f"%{phone.strip()}%"))
	if name:
		stmt = stmt.where(User.name.ilike(f"%{name.strip()}%"))
	if role:
		stmt = stmt.where(User.role == role)

	total_items = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
	accounts = db.execute(
		stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
	).scalars().all()
	total_pages = (total_items + page_size - 1) // page_size
	return PaginatedResponse[UserResponse](
		message="Accounts retrieved successfully.",
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
	current_admin: User = Depends(get_current_admin_only),
	db: Session = Depends(get_db),
):
	account = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
	if not account or account.role not in (UserRole.ADMIN, UserRole.STAFF):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Admin or staff account not found.")

	if payload.email and db.execute(select(User).where(User.email == payload.email.strip().lower(), User.id != user_id)).scalar_one_or_none():
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, message="Email is already in use.")
	if payload.mobile and db.execute(select(User).where(User.mobile == payload.mobile.strip(), User.id != user_id)).scalar_one_or_none():
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, message="Mobile is already in use.")

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
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, message="Account contact messages are already in use.")
	db.refresh(account)
	return ActionResponse(message="Account updated successfully.")


@router.delete(
	"/{user_id}",
	response_model=ActionResponse,
	responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
	summary="Delete an admin or staff profile",
)
def delete_account(
	user_id: uuid.UUID,
	payload: AdminDeleteProfileRequest,
	current_admin: User = Depends(get_current_admin_only),
	db: Session = Depends(get_db),
):
	account = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
	if not account or account.role not in (UserRole.ADMIN, UserRole.STAFF):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Admin or staff account not found.")
	if payload.identifier.strip().lower() != current_admin.email.lower() and payload.identifier.strip() != current_admin.mobile:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, message="OTP identifier must belong to the authenticated administrator.")

	AuthService(db).verify_admin_otp_for_action(
		identifier=payload.identifier,
		otp=payload.otp,
		purpose="DELETE_ACCOUNT",
	)
	account.is_active = False
	db.commit()
	return ActionResponse(message="Account deleted successfully.")

