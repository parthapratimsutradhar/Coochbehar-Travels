import uuid
from collections.abc import AsyncIterator
import mimetypes
from math import ceil

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import AccountRole, DocumentType
from app.models.account import Account
from app.models.document import Document
from app.repository.document_repo import DocumentRepository
from app.schemas.document import (
	CustomerDocumentListResponse,
	CustomerDocumentUploadRequest,
	DocumentDownloadResponse,
)
from app.services.cloudinary_service import promote_cloudinary_asset


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
			file_url=f"/api/v1/documents/{document.id}/file",
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
			customer_id=customer_id,
			uploaded_by=uploaded_by,
		)
		total_pages = ceil(total_items / page_size) if total_items else 0
		return [self._serialize(document, customer_id) for document in documents], total_items, total_pages

	def get_download(self, document_id: uuid.UUID, customer_id: uuid.UUID) -> DocumentDownloadResponse:
		document = self.repo.get_active_by_id(document_id)
		if document is None or document.customer_id != customer_id:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
		return DocumentDownloadResponse(
			document_id=document.id,
			file_name=document.file_name,
			download_url=f"/api/v1/documents/{document.id}/file?download=true",
		)

	async def get_file(
		self,
		document_id: uuid.UUID,
		current_user: Account,
		role: str,
	) -> tuple[Document, AsyncIterator[bytes]]:
		document = self.repo.get_active_by_id(document_id)
		if document is None:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

		if role not in (AccountRole.ADMIN, AccountRole.STAFF):
			if document.customer_id != current_user.id and document.uploaded_by_account_id != current_user.id:
				raise HTTPException(
					status_code=status.HTTP_403_FORBIDDEN,
					detail="You do not have permission to access this document.",
				)

		return document, await self._stream_file(document.file_url)

	@staticmethod
	async def _stream_file(file_url: str) -> AsyncIterator[bytes]:
		if not file_url.startswith(("http://", "https://")):
			async def mock_stream() -> AsyncIterator[bytes]:
				yield b"mock document content"

			return mock_stream()

		client = httpx.AsyncClient(timeout=60.0)
		try:
			request = client.build_request("GET", file_url)
			response = await client.send(request, stream=True)
		except httpx.HTTPError as exc:
			await client.aclose()
			raise HTTPException(
				status_code=status.HTTP_502_BAD_GATEWAY,
				detail="Failed to connect to storage provider.",
			) from exc

		if response.status_code >= 400:
			await response.aclose()
			await client.aclose()
			raise HTTPException(
				status_code=status.HTTP_502_BAD_GATEWAY,
				detail="Unable to fetch document from storage provider.",
			)

		async def stream() -> AsyncIterator[bytes]:
			try:
				async for chunk in response.aiter_bytes(chunk_size=65536):
					yield chunk
			finally:
				await response.aclose()
				await client.aclose()

		return stream()

	async def upload_from_url(
		self,
		payload: CustomerDocumentUploadRequest,
		current_customer: Account,
	) -> None:
		if not (
			payload.file.startswith(("http://", "https://"))
			or "temporary-uploads" in payload.file
		):
			raise HTTPException(status_code=422, detail="file must reference a temporary upload")

		promoted = await promote_cloudinary_asset(payload.file, "customer-documents")
		self.repo.create(
			document_type=payload.document_type,
			title=payload.title.strip(),
			description=payload.description.strip() if payload.description else None,
			customer_id=current_customer.id,
			uploaded_by_account_id=current_customer.id,
			file_url=promoted["url"],
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
		):
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Customer-uploaded document not found.",
			)
		self.repo.soft_delete(document, current_customer.id)