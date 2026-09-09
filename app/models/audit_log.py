
from datetime import datetime
import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class AuditLog(BaseEntity):
    """
    Represents an audit log entry for tracking changes made to entities in the system.
    Contains details about the entity, the action performed, and the user who performed it.
    """
    
    __tablename__ = "audit_logs"

    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True
    )
    
    action: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )
    
    entity_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
         nullable=False
    )
    
    old_values: Mapped[str | None] = mapped_column(
        JSONB,
        nullable=True
     )
    
    new_values: Mapped[str | None] = mapped_column(
        JSONB,
        nullable=True
    )
    
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True
    )
    
    user_agent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
