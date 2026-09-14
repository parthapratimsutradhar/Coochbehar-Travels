import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.enums import AccountRole
from app.models.account import Account
from app.models.document import Document
from app.repository.document_repo import DocumentRepository
from app.schemas.document import AdminDocumentResponse, DocumentResponse, DocumentUpdate
from app.services.cloudinary_service import upload_file_to_cloudinary


class AdminDocumentService:
    def __init__(self, db: Session) -> None:
        self.repo = DocumentRepository(db)

    @staticmethod
    def _date_bounds(
        from_date: date | None,
        to_date: date | None,
    ) -> tuple[datetime | None, datetime | None]:
        if (from_date is None) != (to_date is None):
            raise HTTPException(status_code=422, detail="from_date and to_date must be provided together.")
        if from_date:
            if to_date < from_date:
                raise HTTPException(status_code=422, detail="to_date must be on or after from_date.")
            return (
                datetime.combine(from_date, time.min, tzinfo=timezone.utc),
                datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
            )
        return None, None

    @staticmethod
    def _serialize(document: Document) -> AdminDocumentResponse:
        uploader = document.uploaded_by_account
        customer_upload = uploader is not None and uploader.role == AccountRole.CUSTOMER
        return AdminDocumentResponse(
            id=document.id, document_type=document.document_type, title=document.title,
            description=document.description, customer_id=document.customer_id,
            customer_name=document.customer.name if document.customer else None,
            customer_profile_pic=document.customer.profile_pic if document.customer else None,
            uploaded_by_account_id=document.uploaded_by_account_id, uploaded_at=document.uploaded_at,
            file_url=document.file_url, file_name=document.file_name, mime_type=document.mime_type,
            file_size=document.file_size, uploader_name=uploader.name if uploader else None,
            uploader_profile_pic=uploader.profile_pic if uploader else None,
            type="incoming" if customer_upload else "outgoing",
            is_active=document.is_active,
        )

    def list_documents(self, current_user: Account, **filters: object) -> dict:
        start, end = self._date_bounds(filters.pop("from_date"), filters.pop("to_date"))
        documents, total = self.repo.list_documents(start=start, end=end, **filters)
        page = filters["page"]
        page_size = filters["page_size"]
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": [self._serialize(document) for document in documents],
            "page": page, "page_size": page_size, "total_items": total, "total_pages": total_pages,
        }

    async def upload(self, customer_id: uuid.UUID, file: UploadFile, current_user: Account, **data: object) -> AdminDocumentResponse:
        if not self.repo.get_customer(customer_id):
            raise HTTPException(status_code=404, detail="Customer not found.")
        result = await upload_file_to_cloudinary(file=file, sub_folder="admin-documents")
        document = self.repo.create(
            **data, customer_id=customer_id, uploaded_by_account_id=current_user.id,
            file_url=result["secure_url"], file_name=file.filename or "document",
            mime_type=file.content_type, file_size=result.get("bytes"),
        )

    def update(self, document_id: uuid.UUID, payload: DocumentUpdate) -> None:
        document = self.repo.get_active_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Active document not found.")
        self.repo.update(document, payload.model_dump(exclude_unset=True))

    def bulk_delete(self, document_ids: list[uuid.UUID], current_user: Account) -> int:
        documents = self.repo.list_active_by_ids(document_ids)
        if not documents:
            raise HTTPException(status_code=404, detail="No active documents found to delete.")
        self.repo.bulk_soft_delete(documents, current_user.id)
        return len(documents)
