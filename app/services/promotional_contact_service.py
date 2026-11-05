import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from xml.etree.ElementTree import ParseError

from pydantic import ValidationError
from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.promonal_contact import PromonalContact
from app.schemas.promotional_contact import PromotionalContactCreate


MAX_IMPORT_SIZE = 25 * 1024 * 1024
MAX_IMPORT_RECORDS = 10_000
CONTACT_FIELDS = ("name", "mobile", "email")
EXPORT_MEDIA_TYPES = {
    "json": "application/json",
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class PromotionalContactService:
    def __init__(self, db: Session):
        self.db = db

    def list_contacts(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
    ) -> tuple[list[PromonalContact], int]:
        statement = self._query(search)
        total = self.db.execute(
            select(func.count()).select_from(statement.subquery())
        ).scalar_one()
        contacts = self.db.execute(
            statement.order_by(PromonalContact.id).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return contacts, total

    @staticmethod
    def _query(search: str | None) -> Select[tuple[PromonalContact]]:
        statement = select(PromonalContact)
        if search:
            search_term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    PromonalContact.name.ilike(search_term),
                    PromonalContact.mobile.ilike(search_term),
                    PromonalContact.email.ilike(search_term),
                )
            )
        return statement

    def get_contact(self, contact_id: UUID) -> PromonalContact | None:
        return self.db.get(PromonalContact, contact_id)

    def create_contact(self, values: dict[str, Any]) -> PromonalContact:
        contact = PromonalContact(**values)
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def update_contact(
        self,
        contact: PromonalContact,
        values: dict[str, Any],
    ) -> PromonalContact:
        for field, value in values.items():
            setattr(contact, field, value)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def delete_contact(self, contact: PromonalContact) -> None:
        self.db.delete(contact)
        self.db.commit()

    def export_contacts(
        self,
        file_format: str,
        *,
        search: str | None = None,
    ) -> tuple[bytes, str, str]:
        if file_format not in EXPORT_MEDIA_TYPES:
            raise ValueError("Format must be json, csv, or xlsx")
        contacts = self.db.execute(
            self._query(search).order_by(PromonalContact.id)
        ).scalars().all()
        rows = [
            {field: getattr(contact, field) for field in CONTACT_FIELDS}
            for contact in contacts
        ]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"promotional-contacts-{timestamp}.{file_format}"

        if file_format == "json":
            content = json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")
        elif file_format == "csv":
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, fieldnames=CONTACT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            content = output.getvalue().encode("utf-8")
        else:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Contacts"
            sheet.append(list(CONTACT_FIELDS))
            for row in rows:
                sheet.append([row[field] for field in CONTACT_FIELDS])
            output = io.BytesIO()
            workbook.save(output)
            content = output.getvalue()

        return content, filename, EXPORT_MEDIA_TYPES[file_format]

    def import_contacts(self, content: bytes, file_format: str) -> int:
        if file_format not in EXPORT_MEDIA_TYPES:
            raise ValueError("Format must be json, csv, or xlsx")
        try:
            rows = self._read_import_rows(content, file_format)
            if len(rows) > MAX_IMPORT_RECORDS:
                raise ValueError(f"Import cannot contain more than {MAX_IMPORT_RECORDS} contacts")
            contacts = [
                PromonalContact(**self._validate_import_row(row))
                for row in rows
            ]
            self.db.add_all(contacts)
            self.db.commit()
            return len(contacts)
        except (ValueError, UnicodeDecodeError, InvalidFileException, zipfile.BadZipFile, SQLAlchemyError):
            self.db.rollback()
            raise

    @staticmethod
    def _read_import_rows(content: bytes, file_format: str) -> list[dict[str, Any]]:
        if file_format == "json":
            payload = json.loads(content.decode("utf-8-sig"))
            if isinstance(payload, dict):
                payload = payload.get("contacts")
            if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
                raise ValueError("JSON must contain a list of contact objects")
            return payload

        if file_format == "csv":
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
            if reader.fieldnames is None:
                raise ValueError("CSV file must include a header row")
            return list(reader)

        workbook = None
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            rows = workbook.active.iter_rows(values_only=True)
            headers = next(rows, None)
            if not headers:
                raise ValueError("XLSX file must include a header row")
            fieldnames = [
                str(value).strip().lower() if value is not None else ""
                for value in headers
            ]
            result = []
            for values in rows:
                if not any(value is not None and str(value).strip() for value in values):
                    continue
                result.append(dict(zip(fieldnames, values)))
            return result
        except (InvalidFileException, zipfile.BadZipFile, ParseError, KeyError) as exc:
            raise ValueError("Invalid XLSX file") from exc
        finally:
            if workbook is not None:
                workbook.close()

    @staticmethod
    def _validate_import_row(row: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            if not isinstance(key, str):
                raise ValueError("Contact field names must be strings")
            field = key.strip().lower()
            if field not in CONTACT_FIELDS:
                raise ValueError(f"Unsupported contact field: {field or '(empty)'}")
            if field in normalized:
                raise ValueError(f"Duplicate contact field: {field}")
            normalized[field] = value
        try:
            for field, value in normalized.items():
                if value is not None and not isinstance(value, str):
                    normalized[field] = str(value)
            return PromotionalContactCreate.model_validate(normalized).model_dump()
        except ValidationError as exc:
            raise ValueError(f"Invalid contact row: {exc}") from exc
