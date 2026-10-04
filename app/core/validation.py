import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Enum as SQLAlchemyEnum


def validate_backup_manifest(
    manifest: Any,
    *,
    format_name: str,
    version: int,
    valid_groups: set[str],
    group_tables: dict[str, set[str]],
) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    if not isinstance(manifest, dict) or manifest.get("format") != format_name:
        raise ValueError("Unsupported backup file")
    if manifest.get("version") != version:
        raise ValueError("Unsupported backup version")
    groups = manifest.get("groups")
    if not isinstance(groups, list) or not groups or not all(
        isinstance(group, str) and group in valid_groups for group in groups
    ):
        raise ValueError("Backup has invalid data groups")
    allowed_tables = set().union(*(group_tables[group] for group in groups))
    tables = manifest.get("tables")
    if not isinstance(tables, dict) or not set(tables) <= allowed_tables:
        raise ValueError("Backup contains tables that were not selected")
    for table_name, rows in tables.items():
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"Backup table {table_name} must contain record objects")
    return tables, set(groups)


def deserialize_backup_row(model: type, row: dict[str, Any]) -> dict[str, Any]:
    columns = {column.name: column for column in model.__table__.columns}
    unknown_fields = set(row) - set(columns)
    if unknown_fields:
        raise ValueError(f"Unknown fields for {model.__tablename__}: {', '.join(sorted(unknown_fields))}")
    if "id" not in row:
        raise ValueError(f"Every {model.__tablename__} record must include its id")
    values = {}
    for field_name, value in row.items():
        column = columns[field_name]
        if value is None:
            values[field_name] = None
            continue
        column_type = column.type
        python_type = column_type.python_type
        if isinstance(column_type, SQLAlchemyEnum):
            enum_class = column_type.enum_class
            try:
                values[field_name] = enum_class(value)
            except ValueError:
                try:
                    values[field_name] = enum_class[value]
                except KeyError as exc:
                    raise ValueError(f"Invalid enum value for {field_name}") from exc
        elif python_type is uuid.UUID:
            values[field_name] = uuid.UUID(str(value))
        elif python_type is datetime:
            values[field_name] = datetime.fromisoformat(value)
        elif python_type is date:
            values[field_name] = date.fromisoformat(value)
        elif python_type is Decimal:
            values[field_name] = Decimal(str(value))
        elif python_type is bool:
            if not isinstance(value, bool):
                raise ValueError(f"Invalid boolean value for {field_name}")
            values[field_name] = value
        elif python_type is int:
            values[field_name] = int(value)
        else:
            values[field_name] = value
    return values


def validate_backup_account_role(
    values: dict[str, Any],
    groups: set[str],
    *,
    customer_role: Any,
    staff_role: Any,
    admin_role: Any,
) -> None:
    role = values.get("role")
    if role == admin_role:
        raise ValueError("Admin accounts cannot be imported from a backup")
    if role == customer_role and "customers" not in groups:
        raise ValueError("Customer account records require the customers group")
    if role == staff_role and "staff" not in groups:
        raise ValueError("Staff account records require the staff group")
    if role not in {customer_role, staff_role}:
        raise ValueError("Backup contains an invalid account role")