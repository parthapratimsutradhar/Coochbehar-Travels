import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.user import User


class UserRepository:
    """Repository for User data access operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key ID."""
        stmt = select(User).where(User.id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        """Fetch user by lowercase email."""
        stmt = select(User).where(User.email.ilike(email.strip()))
        return self.db.execute(stmt).scalar_one_or_none()

    def update_last_login(self, user: User) -> None:
        """Update last_login timestamp."""
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)

    def create_user(
        self,
        name: str,
        email: str,
        mobile: str,
        role: UserRole = UserRole.ADMIN,
        user_code: str | None = None,
    ) -> User:
        """Create and persist a new user."""
        if not user_code:
            user_code = f"USR-{uuid.uuid4().hex[:8].upper()}"

        user = User(
            user_code=user_code,
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
