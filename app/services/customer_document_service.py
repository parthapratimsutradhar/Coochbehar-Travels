import uuid
import mimetypes
from math import ceil
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import (
	AccountRole,
	BOOKING_DOCUMENT_TYPES,
	IDENTITY_DOCUMENT_TYPES,
	DocumentType,
)
from app.models.account import Account
from app.models.document import Document
from app.repository.document_repo import DocumentRepository
from app.schemas.document import (
	CustomerDocumentListResponse,
	BookingDocumentListResponse,
	CustomerDocumentUploadRequest,
	DocumentDownloadResponse,
)
from app.services.cdn_service import get_private_document_path, promote_cdn_asset


class CustomerDocumentService:
	def __init__(self, db: Session) -> None:
		self.repo = DocumentRepository(db)

	@staticmethod
	def _serialize(document: Document, customer_id: uuid.UUID) -> CustomerDocumentListResponse:
		uploader = document.uploaded_by_account
		is_current_customer_upload = document.uploaded_by_account_id == customer_id
		return CustomerDocumentListResponse(
			id=document.id,
			document_type=document.document_type,
			title=document.title,
			description=document.description,
			customer_id=document.customer_id,
			uploaded_by_account_id=document.uploaded_by_account_id,
			uploaded_at=document.uploaded_at,
			file_name=document.file_name,
			mime_type=document.mime_type,
			file_size=document.file_size,
			file_url=f"/api/v1/documents/{document.id}/download",
			customer_name=document.customer.name if document.customer else None,
			customer_profile_pic=document.customer.profile_pic if document.customer else None,
			uploader_name=uploader.name if uploader else None,
			uploader_profile_pic=uploader.profile_pic if uploader else None,
			type="outgoing" if is_current_customer_upload else "incoming",
			can_delete=is_current_customer_upload,
		)

	def list_documents(
		self,
		customer_id: uuid.UUID,
		page: int,
		page_size: int,
		document_type: DocumentType | None,
		uploaded_by: str | None,
	) -> tuple[list[CustomerDocumentListResponse], int, int]:
		documents, total_items = self.repo.list_documents(
			page=page,
			page_size=page_size,
			document_type=document_type,
			document_types=IDENTITY_DOCUMENT_TYPES,
			customer_id=customer_id,
			uploaded_by=uploaded_by,
		)
		total_pages = ceil(total_items / page_size) if total_items else 0
		return [self._serialize(document, customer_id) for document in documents], total_items, total_pages

	@staticmethod
	def _serialize_booking_document(
		document: Document,
		customer_id: uuid.UUID,
	) -> BookingDocumentListResponse:
		uploader = document.uploaded_by_account
		return BookingDocumentListResponse(
			id=document.id,
			document_type=document.document_type,
			booking_id=document.booking_id,
			booking_code=document.booking.booking_code,
			title=document.title,
			description=document.description,
			uploaded_by_account_id=document.uploaded_by_account_id,
			uploader_name=uploader.name if uploader else None,
			uploader_profile_pic=uploader.profile_pic if uploader else None,
			uploaded_at=document.uploaded_at,
			file_url=f"/api/v1/documents/{document.id}/download",
			file_name=document.file_name,
			mime_type=document.mime_type,
			file_size=document.file_size,
			type="outgoing" if document.uploaded_by_account_id == customer_id else "incoming",
			can_delete=(
				document.uploaded_by_account_id == customer_id
				and document.document_type in IDENTITY_DOCUMENT_TYPES
			),
		)

	def list_booking_documents(
		self,
		customer_id: uuid.UUID,
		page: int,
		page_size: int,
		booking_id: uuid.UUID | None = None,
	) -> tuple[list[BookingDocumentListResponse], int, int]:
		if booking_id is not None:
			booking = self.repo.get_booking(booking_id)
			if booking is None or booking.customer_id != customer_id:
				raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

		documents, total_items = self.repo.list_documents(
			page=page,
			page_size=page_size,
			customer_id=customer_id,
			document_types=None if booking_id is not None else BOOKING_DOCUMENT_TYPES,
			booking_id=booking_id,
			booking_required=booking_id is None,
		)
		total_pages = ceil(total_items / page_size) if total_items else 0
		items = [self._serialize_booking_document(document, customer_id) for document in documents]
		return items, total_items, total_pages

	def get_download(self, document_id: uuid.UUID, customer_id: uuid.UUID) -> DocumentDownloadResponse:
		document = self.repo.get_active_by_id(document_id)
		if document is None or document.customer_id != customer_id:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
		return DocumentDownloadResponse(
			document_id=document.id,
			file_name=document.file_name,
			download_url=f"/api/v1/documents/{document.id}/download",
		)

	async def get_file(
		self,
		document_id: uuid.UUID,
		current_user: Account,
		role: str,
	) -> tuple[Document, Path]:
		document = self.repo.get_active_by_id(document_id)
		if document is None:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

		if role not in (AccountRole.ADMIN, AccountRole.STAFF, "ADMIN", "STAFF"):
			if document.customer_id != current_user.id:
				raise HTTPException(
					status_code=status.HTTP_404_NOT_FOUND,
					detail="Document not found.",
				)

		return document, get_private_document_path(document.file_url)

	async def upload_from_url(
		self,
		payload: CustomerDocumentUploadRequest,
		current_customer: Account,
	) -> None:
		if payload.document_type not in IDENTITY_DOCUMENT_TYPES:
			raise HTTPException(
				status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
				detail="Customers may only upload ID_PROOF or ADDRESS_PROOF documents.",
			)
		promoted = await promote_cdn_asset(payload.file, "private/customer-documents")
		self.repo.create(
			document_type=payload.document_type,
			title=payload.title.strip(),
			description=payload.description.strip() if payload.description else None,
			customer_id=current_customer.id,
			uploaded_by_account_id=current_customer.id,
			file_url=promoted["path"],
			file_name=payload.file_name,
			mime_type=mimetypes.guess_type(payload.file_name)[0] or "application/octet-stream",
			file_size=None,
		)

	def delete(self, document_id: uuid.UUID, current_customer: Account) -> None:
		document = self.repo.get_active_by_id(document_id)
		if (
			document is None
			or document.customer_id != current_customer.id
			or document.uploaded_by_account_id != current_customer.id
			or document.document_type not in IDENTITY_DOCUMENT_TYPES
		):
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Customer-uploaded document not found.",
			)
		self.repo.soft_delete(document, current_customer.id)