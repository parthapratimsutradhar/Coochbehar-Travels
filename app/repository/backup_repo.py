from typing import Any

from sqlalchemy import Index, UniqueConstraint, literal, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.types import JSON

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

    def insert_if_missing(self, model: type, values: dict[str, Any]) -> tuple[bool, Any]:
        record = self.db.get(model, values["id"])
        if record is not None:
            return False, record
        unique_column_sets = [
            (tuple(constraint.columns), None)
            for constraint in model.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        ]
        unique_column_sets.extend(
            (
                tuple(index.columns),
                index.dialect_options[self.db.get_bind().dialect.name].get("where"),
            )
            for index in model.__table__.indexes
            if isinstance(index, Index) and index.unique
        )
        for columns, predicate in unique_column_sets:
            if any(values.get(column.name) is None for column in columns):
                continue
            if predicate is not None:
                if isinstance(predicate, TextClause):
                    candidate = select(
                        *(
                            literal(values[column.name], type_=column.type).label(column.name)
                            for column in model.__table__.columns
                            if column.name in values and not isinstance(column.type, JSON)
                        )
                    ).subquery(model.__tablename__)
                    applies_to_values = self.db.scalar(
                        select(literal(True)).select_from(candidate).where(predicate)
                    ) is not None
                else:
                    value_predicate = visitors.replacement_traverse(
                        predicate,
                        {},
                        lambda element: literal(values[element.name])
                        if getattr(element, "name", None) in values
                        else None,
                    )
                    applies_to_values = self.db.scalar(
                        select(literal(True)).where(value_predicate)
                    ) is not None
                if not applies_to_values:
                    continue
            statement = select(model).where(
                *(column == values[column.name] for column in columns)
            )
            if predicate is not None:
                statement = statement.where(predicate)
            record = self.db.scalar(statement.limit(1))
            if record is not None:
                return False, record
        comparable_columns = [
            column
            for column in model.__table__.columns
            if column.name not in {"id", "created_at", "updated_at"}
            and column.name in values
            and not isinstance(column.type, JSON)
        ]
        if comparable_columns:
            exact_match = self.db.scalar(
                select(model)
                .where(
                    *(
                        column.is_(None)
                        if values[column.name] is None
                        else column == values[column.name]
                        for column in comparable_columns
                    )
                )
                .limit(1)
            )
            if exact_match is not None:
                return False, exact_match
        record = model()
        for field_name, value in values.items():
            setattr(record, field_name, value)
        self.db.add(record)
        self.db.flush()
        return True, record