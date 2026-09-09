import uuid
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AccountRole
from app.models.account import Account


class UserRepository:
    """Repository for User/Account data access operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> Account | None:
        """Fetch user by primary key ID."""
        stmt = select(Account).where(Account.id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Account | None:
        """Fetch an admin or staff user by lowercase email."""
        stmt = select(Account).where(
            Account.email.ilike(email.strip()),
            Account.role.in_([AccountRole.ADMIN, AccountRole.STAFF]),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_mobile(self, mobile: str) -> Account | None:
        """Fetch an admin or staff user by mobile number."""
        stmt = select(Account).where(
            Account.mobile == mobile.strip(),
            Account.role.in_([AccountRole.ADMIN, AccountRole.STAFF]),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update_last_login(self, user: Account) -> None:
        """Update last_login timestamp."""
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)

    def create_user(
        self,
        name: str,
        email: str,
        mobile: str,
        role: AccountRole = AccountRole.ADMIN,
        user_code: str | None = None,
    ) -> Account:
        """Create and persist a new user."""
        code = user_code or f"USR-{uuid.uuid4().hex[:8].upper()}"

        user = Account(
            account_code=code,
            name=name,
            email=email.strip().lower(),
            mobile=mobile.strip(),
            role=role,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_staff_users(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Account], int]:
        stmt = select(Account).where(Account.role.in_([AccountRole.ADMIN, AccountRole.STAFF]))
        if is_active is not None:
            stmt = stmt.where(Account.is_active == is_active)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Account.name.ilike(term)
                | Account.email.ilike(term)
                | Account.mobile.ilike(term)
                | Account.account_code.ilike(term)
            )
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        users = self.db.execute(
            stmt.order_by(Account.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(users), total
