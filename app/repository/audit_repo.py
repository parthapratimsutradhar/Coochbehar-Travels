import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_change(
        self,
        *,
        account_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        old_values: dict,
        new_values: dict,
    ) -> AuditLog:
        audit_log = AuditLog(
            account_id=account_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
        )
        self.db.add(audit_log)
        return audit_log
