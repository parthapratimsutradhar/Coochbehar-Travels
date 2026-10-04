from typing import Any

from sqlalchemy import Index, UniqueConstraint, select
from sqlalchemy.orm import Session

from app.core.enums import AccountRole
from app.models.account import Account


class BackupRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_rows(
        self,
        model: type,
        *,
        role: AccountRole | None = None,
        filters: dict[str, list[Any]] | None = None,
    ) -> list[Any]:
        statement = select(model)
        if role is not None:
            if model is not Account:
                raise ValueError("Role filters are only supported for account records")
            statement = statement.where(Account.role == role)
        for field_name, values in (filters or {}).items():
            if not hasattr(model, field_name):
                raise ValueError(f"Unknown backup filter: {field_name}")
            if not values:
                return []
            statement = statement.where(getattr(model, field_name).in_(values))
        return list(self.db.scalars(statement).all())

    def get_by_id(self, model: type, record_id: Any) -> Any | None:
        return self.db.get(model, record_id)

    def insert_if_missing(self, model: type, values: dict[str, Any]) -> bool:
        record = self.db.get(model, values["id"])
        if record is not None:
            return False
        unique_column_sets = [
            tuple(constraint.columns)
            for constraint in model.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        ]
        unique_column_sets.extend(
            tuple(index.columns)
            for index in model.__table__.indexes
            if isinstance(index, Index) and index.unique
        )
        for columns in unique_column_sets:
            if any(values.get(column.name) is None for column in columns):
                continue
            statement = select(model).where(
                *(column == values[column.name] for column in columns)
            )
            if self.db.scalar(statement.limit(1)) is not None:
                return False
        record = model()
        for field_name, value in values.items():
            setattr(record, field_name, value)
        self.db.add(record)
        self.db.flush()
        return True