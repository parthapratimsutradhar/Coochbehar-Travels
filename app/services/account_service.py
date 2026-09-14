import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.enums import AccountRole
from app.core.messages.error import AccessError, UserError
from app.repository.account_repo import AccountRepository
from app.schemas.account import AdminDeleteProfileRequest, AdminProfileUpdate, AdminStaffCreate
from app.services.auth_service import AuthService
from app.services.cloudinary_service import promote_cloudinary_asset
from app.models.account import Account


class AdminAccountService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = AccountRepository(db)
        self.auth_service = AuthService(db)

    @staticmethod
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

    @staticmethod
    def _ensure_delete_permission(current_user: Account, account: Account) -> None:
        if current_user.role == AccountRole.ADMIN:
            if account.role == AccountRole.ADMIN and account.id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)
            return

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.ADMIN_REQUIRED)

    def list_accounts(
        self,
        current_admin: Account,
        page: int,
        page_size: int,
        search: str | None = None,
        role: AccountRole | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Account], int, int]:
        accounts, total_items = self.repo.list_admin_staff(
            current_admin_id=current_admin.id,
            page=page,
            page_size=page_size,
            search=search,
            role=role,
            is_active=is_active,
        )
        total_pages = (total_items + page_size - 1) // page_size if total_items else 0
        return accounts, total_items, total_pages

    async def create_staff(self, payload: AdminStaffCreate) -> Account:
        if payload.role != AccountRole.STAFF:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=UserError.STAFF_ONLY,
            )

        email = payload.email.strip().lower()
        mobile = payload.mobile.strip()
        if self.repo.exists_email_for_role(email, AccountRole.STAFF):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.EMAIL_ALREADY_EXISTS)
        if self.repo.exists_mobile_for_role(mobile, AccountRole.STAFF):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.MOBILE_ALREADY_EXISTS)

        profile_pic = payload.profile_pic.strip() if payload.profile_pic else None
        if profile_pic:
            promoted = await promote_cloudinary_asset(
                profile_pic,
                "profile-picture",
                resource_type="image",
            )
            profile_pic = promoted["url"]

        try:
            return self.repo.create_staff(
                name=payload.name.strip(),
                email=email,
                mobile=mobile,
                profile_pic=profile_pic,
                is_active=payload.is_active,
            )
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.CONTACT_ALREADY_EXISTS)

    async def update_account(self, current_user: Account, user_id: uuid.UUID, payload: AdminProfileUpdate) -> Account:
        account = self.repo.get_admin_staff_by_id(user_id)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=UserError.USER_NOT_FOUND)

        self._ensure_update_permission(current_user, account)

        target_role = payload.role or account.role
        email = payload.email.strip().lower() if payload.email else None
        mobile = payload.mobile.strip() if payload.mobile else None

        if email and self.repo.exists_email_for_role(email, target_role, exclude_id=user_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.EMAIL_ALREADY_EXISTS)
        if mobile and self.repo.exists_mobile_for_role(mobile, target_role, exclude_id=user_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.MOBILE_ALREADY_EXISTS)

        update_data = payload.model_dump(exclude_unset=True)
        if "email" in update_data:
            update_data["email"] = update_data["email"].strip().lower()
        if "mobile" in update_data:
            update_data["mobile"] = update_data["mobile"].strip()
        if "profile_pic" in update_data:
            profile_pic = update_data["profile_pic"].strip() if update_data["profile_pic"] else None
            if profile_pic:
                promoted = await promote_cloudinary_asset(
                    profile_pic,
                    "profile-picture",
                    resource_type="image",
                )
                profile_pic = promoted["url"]
            update_data["profile_pic"] = profile_pic

        for field, value in update_data.items():
            setattr(account, field, value)

        try:
            self.repo.save(account)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=UserError.CONTACT_ALREADY_EXISTS)

        return account

    def delete_account(self, current_user: Account, user_id: uuid.UUID, payload: AdminDeleteProfileRequest) -> Account:
        account = self.repo.get_admin_staff_by_id(user_id)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=UserError.USER_NOT_FOUND)

        self._ensure_delete_permission(current_user, account)

        identifier = payload.identifier.strip()
        if identifier.lower() != current_user.email.lower() and identifier != current_user.mobile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=AccessError.OTP_ADMIN_REQUIRED)

        self.auth_service.verify_admin_otp_for_action(
            identifier=payload.identifier,
            otp=payload.otp,
            purpose="DELETE_ACCOUNT",
        )
        self.repo.soft_delete(account)
        return account
