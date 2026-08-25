from sqlalchemy import Enum, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.enums import UserRole
from app.models.base import ActiveEntity


class User(ActiveEntity):
    __tablename__ = "users"

    user_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    mobile: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.ADMIN,
        nullable=False,
    )
    
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    profile_pic: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

# ── Relationships ───────────────────────────────────────────────────────
    lead_activities = relationship(
        "LeadActivity",
        back_populates="user",
    )

    auth_sessions = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    documents_uploaded = relationship(
        "Document",
        foreign_keys="Document.uploaded_by_user_id",
        back_populates="uploaded_by_user",
    )

    documents_deleted = relationship(
        "Document",
        foreign_keys="Document.deleted_by_user_id",
        back_populates="deleted_by_user",
    )