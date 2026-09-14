import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import AccountRole, DocumentType
from app.models.account import Account
from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_documents(
        self,
        page: int,
        page_size: int,
        start: datetime | None = None,
        end: datetime | None = None,
        document_type: DocumentType | None = None,
        document_status: str = "active",
        customer_id: uuid.UUID | None = None,
        uploaded_by: str | None = None,
    ) -> tuple[list[Document], int]:
        stmt = select(Document).options(
            joinedload(Document.customer),
            joinedload(Document.uploaded_by_account),
        )
        if document_status == "active":
            stmt = stmt.where(Document.is_active.is_(True))
        elif document_status == "deleted":
            stmt = stmt.where(Document.is_active.is_(False))
        if customer_id:
            stmt = stmt.where(Document.customer_id == customer_id)
        if document_type:
            stmt = stmt.where(Document.document_type == document_type)
        if uploaded_by:
            role = AccountRole.CUSTOMER if uploaded_by == "CUSTOMER" else AccountRole.ADMIN
            stmt = stmt.join(Document.uploaded_by_account).where(
                Account.role == role if role == AccountRole.CUSTOMER else Account.role != AccountRole.CUSTOMER
            )
        if start:
            stmt = stmt.where(Document.uploaded_at >= start, Document.uploaded_at < end)

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        documents = self.db.execute(
            stmt.order_by(Document.uploaded_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().unique().all()
        return list(documents), total

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return self.db.execute(
            select(Document)
            .options(
                joinedload(Document.customer),
                joinedload(Document.uploaded_by_account),
            )
            .where(Document.id == document_id)
        ).unique().scalar_one_or_none()

    def get_active_by_id(self, document_id: uuid.UUID) -> Document | None:
        return self.db.execute(
            select(Document)
            .options(
                joinedload(Document.customer),
                joinedload(Document.uploaded_by_account),
            )
            .where(Document.id == document_id, Document.is_active.is_(True))
        ).unique().scalar_one_or_none()

    def get_customer(self, customer_id: uuid.UUID) -> Account | None:
        return self.db.execute(
            select(Account).where(
                Account.id == customer_id,
                Account.role == AccountRole.CUSTOMER,
                Account.is_active.is_(True),
            )
        ).scalar_one_or_none()

    def create(self, **data: object) -> Document:
        document = Document(**data)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return self.get_by_id(document.id) or document

    def update(self, document: Document, data: dict[str, object]) -> None:
        for field, value in data.items():
            setattr(document, field, value)
        self.db.commit()

    def soft_delete(self, document: Document, deleted_by_account_id: uuid.UUID) -> None:
        document.is_active = False
        document.deleted_at = datetime.now().astimezone()
        document.deleted_by_account_id = deleted_by_account_id
        self.db.commit()

    def bulk_soft_delete(self, documents: list[Document], deleted_by_account_id: uuid.UUID) -> None:
        deleted_at = datetime.now().astimezone()
        for document in documents:
            document.is_active = False
            document.deleted_at = deleted_at
            document.deleted_by_account_id = deleted_by_account_id
        self.db.commit()

    def list_active_by_ids(self, document_ids: list[uuid.UUID]) -> list[Document]:
        return list(self.db.execute(
            select(Document).where(
                Document.id.in_(document_ids),
                Document.is_active.is_(True),
            )
        ).scalars().all())
