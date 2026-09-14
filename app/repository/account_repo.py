import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AccountRole
from app.models.account import Account


class AccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_admin_staff_by_id(self, user_id: uuid.UUID) -> Account | None:
        stmt = select(Account).where(
            Account.id == user_id,
            Account.role.in_((AccountRole.ADMIN, AccountRole.STAFF)),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create_staff(
        self,
        name: str,
        email: str,
        mobile: str,
        profile_pic: str | None,
        is_active: bool,
    ) -> Account:
        account = Account(
            account_code=f"USR-{uuid.uuid4().hex[:8].upper()}",
            name=name,
            email=email,
            mobile=mobile,
            role=AccountRole.STAFF,
            profile_pic=profile_pic,
            is_active=is_active,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def list_admin_staff(
        self,
        current_admin_id: uuid.UUID,
        page: int,
        page_size: int,
        search: str | None = None,
        role: AccountRole | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Account], int]:
        stmt = select(Account).where(
            Account.role.in_((AccountRole.ADMIN, AccountRole.STAFF)),
            Account.id != current_admin_id,
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

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        accounts = self.db.execute(
            stmt.order_by(Account.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(accounts), total_items

    def exists_email_for_role(self, email: str, role: AccountRole, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Account.id).where(
            Account.email == email,
            Account.role == role,
        )
        if exclude_id is not None:
            stmt = stmt.where(Account.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def exists_mobile_for_role(self, mobile: str, role: AccountRole, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Account.id).where(
            Account.mobile == mobile,
            Account.role == role,
        )
        if exclude_id is not None:
            stmt = stmt.where(Account.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def save(self, account: Account) -> None:
        self.db.commit()
        self.db.refresh(account)

    def soft_delete(self, account: Account) -> None:
        account.is_active = False
        self.db.commit()
