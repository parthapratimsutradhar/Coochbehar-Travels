import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_admin_only
from app.core.enums import DocumentType
from app.db.database import get_db
from app.models.customer import Customer
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.cloudinary_service import upload_file_to_cloudinary


class BulkDeleteDocumentsRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(..., min_length=1)


router = APIRouter(prefix="/admin/documents", tags=["Admin Documents"])


@router.get(
    "",
    response_model=PaginatedResponse[DocumentResponse],
    responses={401: {"model": ErrorResponse}}
    )
def list_customer_documents(
	customer_id: uuid.UUID | None = Query(None),
	page: int = Query(1, ge=1),
	page_size: int = Query(10, ge=1, le=100),
	current_user: User = Depends(get_current_admin),
	db: Session = Depends(get_db),
) -> PaginatedResponse[DocumentResponse]:
	query = db.query(Document).filter(Document.is_active.is_(True))
	if customer_id:
		query = query.filter(Document.customer_id == customer_id)
	total_items = query.count()
	documents = query.order_by(Document.uploaded_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
	total_pages = (total_items + page_size - 1) // page_size if total_items else 0
	data = [
		DocumentResponse(
			**{field: getattr(document, field) for field in (
				"id", "document_type", "title", "description",
				"customer_id", "uploaded_by_customer_id", "uploaded_by_user_id",
				"uploaded_at", "file_url", "file_name", "mime_type", "file_size",
			)},
			customer_name=document.customer.name if document.customer else None,
			customer_profile_pic=document.customer.profile_pic if document.customer else None,
			uploader_name=(document.uploaded_by_customer or document.uploaded_by_user).name
			if document.uploaded_by_customer or document.uploaded_by_user else None,
			uploader_profile_pic=(document.uploaded_by_customer or document.uploaded_by_user).profile_pic
			if document.uploaded_by_customer or document.uploaded_by_user else None,
			uploaded_by="CUSTOMER" if document.uploaded_by_customer_id else "ADMIN",
			can_delete=False,
		)
		for document in documents
	]
	return PaginatedResponse(
		message="Customer documents fetched successfully",
		data=data,
		pagination=PaginationMeta(
			current_page=page, page_size=page_size, total_items=total_items,
			total_pages=total_pages, has_next=page < total_pages, has_previous=page > 1,
		),
	)


@router.post(
    "",
    response_model=SuccessResponse[DocumentResponse],
    status_code=status.HTTP_201_CREATED
    )
async def upload_customer_document(
	customer_id: uuid.UUID = Form(...),
	file: UploadFile = File(...),
	document_type: DocumentType = Form(...),
	title: str = Form(..., min_length=1, max_length=200),
	description: str | None = Form(None),
	current_user: User = Depends(get_current_admin),
	db: Session = Depends(get_db),
) -> SuccessResponse[DocumentResponse]:
	if db.query(Customer.id).filter(Customer.id == customer_id).first() is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
	result = await upload_file_to_cloudinary(file=file, sub_folder="admin-documents")
	document = Document(
		document_type=document_type,
		title=title.strip(),
		description=description,
		customer_id=customer_id,
		uploaded_by_user_id=current_user.id,
		file_url=result["secure_url"],
		file_name=file.filename or "document",
		mime_type=file.content_type,
		file_size=result.get("bytes"),
	)
	db.add(document)
	db.commit()
	db.refresh(document)
	return SuccessResponse(message="Document uploaded successfully", data=DocumentResponse(
		**{field: getattr(document, field) for field in (
			"id", "document_type", "title", "description",
			"customer_id", "uploaded_by_customer_id", "uploaded_by_user_id",
			"uploaded_at", "file_url", "file_name", "mime_type", "file_size",
		)},
		customer_name=document.customer.name if document.customer else None,
		customer_profile_pic=document.customer.profile_pic if document.customer else None,
		uploader_name=document.uploaded_by_user.name if document.uploaded_by_user else None,
		uploader_profile_pic=document.uploaded_by_user.profile_pic if document.uploaded_by_user else None,
		uploaded_by="ADMIN",
		can_delete=False,
	))

@router.delete(
    "/bulk",
    response_model=ActionResponse,
    summary="Bulk delete customer documents",
)
def bulk_delete_documents(
    payload: BulkDeleteDocumentsRequest,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    documents = db.query(Document).filter(Document.id.in_(payload.document_ids), Document.is_active.is_(True)).all()
    if not documents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active documents found to delete.")

    for document in documents:
        document.is_active = False
        document.deleted_at = datetime.utcnow()
        document.deleted_by_user_id = current_user.id

    db.commit()
    return ActionResponse(message=f"{len(documents)} document(s) deleted successfully")