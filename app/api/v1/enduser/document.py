import uuid
from datetime import datetime, timezone
from math import ceil

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.enums import DocumentType
from app.db.database import get_db
from app.models.customer import Customer
from app.models.document import Document
from app.schemas.document import DocumentDownloadResponse, DocumentResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.cloudinary_service import upload_file_to_cloudinary

router = APIRouter(
	prefix="/documents",
	tags=["Documents"],
)


def _serialize_document(document: Document, customer_id: uuid.UUID) -> DocumentResponse:
	is_customer_upload = document.uploaded_by_customer_id == customer_id
	uploader = document.uploaded_by_customer or document.uploaded_by_user
	return DocumentResponse(
		**{field: getattr(document, field) for field in (
			"id", "document_type", "title", "description",
			"customer_id", "uploaded_by_customer_id", "uploaded_by_user_id",
			"uploaded_at", "file_url", "file_name", "mime_type", "file_size",
		)},
		customer_name=document.customer.name if document.customer else None,
		customer_profile_pic=document.customer.profile_pic if document.customer else None,
		uploader_name=uploader.name if uploader else None,
		uploader_profile_pic=uploader.profile_pic if uploader else None,
		uploaded_by="CUSTOMER" if is_customer_upload else "ADMIN",
		can_delete=is_customer_upload,
		type= "outgoing" if is_customer_upload else "incoming",
	)


@router.get(
	"",
	response_model=PaginatedResponse[DocumentResponse],
	responses={401: {"model": ErrorResponse}},
	summary="List the customer's documents",
	description="Return active documents belonging to the authenticated customer, including customer and admin uploads.",
)
def list_documents(
	page: int = Query(1, ge=1),
	page_size: int = Query(10, ge=1, le=100),
	document_type: DocumentType | None = Query(None),
	uploaded_by: str | None = Query(None, pattern="^(CUSTOMER|ADMIN)$"),
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> PaginatedResponse[DocumentResponse]:
	query = db.query(Document).filter(
		Document.customer_id == current_customer.id,
		Document.is_active.is_(True),
	)
	if document_type:
		query = query.filter(Document.document_type == document_type)
	if uploaded_by == "CUSTOMER":
		query = query.filter(Document.uploaded_by_customer_id == current_customer.id)
	elif uploaded_by == "ADMIN":
		query = query.filter(Document.uploaded_by_user_id.is_not(None))

	total_items = query.count()
	documents = query.order_by(Document.uploaded_at.desc()).offset(
		(page - 1) * page_size
	).limit(page_size).all()
	total_pages = ceil(total_items / page_size) if total_items else 0
	return PaginatedResponse(
		message="Documents fetched successfully",
		data=[_serialize_document(document, current_customer.id) for document in documents],
		pagination=PaginationMeta(
			current_page=page,
			page_size=page_size,
			total_items=total_items,
			total_pages=total_pages,
			has_next=page < total_pages,
			has_previous=page > 1,
		),
	)


@router.get(
	"/{document_id}/download",
	response_model=SuccessResponse[DocumentDownloadResponse],
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Get a document download URL",
)
def download_document(
	document_id: uuid.UUID,
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> SuccessResponse[DocumentDownloadResponse]:
	document = db.query(Document).filter(
		Document.id == document_id,
		Document.customer_id == current_customer.id,
		Document.is_active.is_(True),
	).first()
	if document is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
	return SuccessResponse(
		message="Document download URL generated successfully",
		data=DocumentDownloadResponse(
			document_id=document.id,
			file_name=document.file_name,
			download_url=document.file_url,
		),
	)


@router.post(
	"",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
	summary="Upload a customer document",
)
async def upload_document(
	file: UploadFile = File(...),
	document_type: DocumentType = Form(...),
	title: str = Form(..., min_length=1, max_length=200),
	description: str | None = Form(None),
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	result = await upload_file_to_cloudinary(file=file, sub_folder="customer-documents")
	document = Document(
		document_type=document_type,
		title=title.strip(),
		description=description,
		customer_id=current_customer.id,
		uploaded_by_customer_id=current_customer.id,
		file_url=result["secure_url"],
		file_name=file.filename or "document",
		mime_type=file.content_type,
		file_size=result.get("bytes"),
	)
	db.add(document)
	db.commit()
	db.refresh(document)
	return ActionResponse(message="Document uploaded successfully")


@router.delete(
	"/{document_id}",
	response_model=ActionResponse,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Delete a customer-uploaded document",
)
def delete_document(
	document_id: uuid.UUID,
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	document = db.query(Document).filter(
		Document.id == document_id,
		Document.customer_id == current_customer.id,
		Document.uploaded_by_customer_id == current_customer.id,
		Document.is_active.is_(True),
	).first()
	if document is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer-uploaded document not found.")
	document.is_active = False
	document.deleted_at = datetime.now(timezone.utc)
	document.deleted_by_customer_id = current_customer.id
	db.commit()
	return ActionResponse(message="Document deleted successfully")
