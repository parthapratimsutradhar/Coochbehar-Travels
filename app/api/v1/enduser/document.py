import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_current_customer
from app.core.enums import DocumentType
from app.db.database import get_db
from app.models.account import Account
from app.schemas.document import (
	CustomerDocumentListResponse,
	CustomerDocumentUploadRequest,
	DocumentDownloadResponse,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.customer_document_service import CustomerDocumentService

router = APIRouter(
	prefix="/documents",
	tags=["Documents"],
)


@router.get(
	"",
	response_model=PaginatedResponse[CustomerDocumentListResponse],
	responses={401: {"model": ErrorResponse}},
	summary="List the customer's documents",
	description="Return active documents belonging to the authenticated customer, including customer and admin uploads.",
)
def list_documents(
	page: int = Query(1, ge=1),
	page_size: int = Query(10, ge=1, le=100),
	document_type: DocumentType | None = Query(None),
	uploaded_by: str | None = Query(None, pattern="^(CUSTOMER|ADMIN)$"),
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> PaginatedResponse[CustomerDocumentListResponse]:
	items, total_items, total_pages = CustomerDocumentService(db).list_documents(
		customer_id=current_customer.id,
		page=page,
		page_size=page_size,
		document_type=document_type,
		uploaded_by=uploaded_by,
	)
	return PaginatedResponse(
		message="Items fetched successfully",
		data=items,
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
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> SuccessResponse[DocumentDownloadResponse]:
	return SuccessResponse(
		message="Document download URL generated successfully",
		data=CustomerDocumentService(db).get_download(
			document_id=document_id,
			customer_id=current_customer.id,
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
	payload: CustomerDocumentUploadRequest,
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	await CustomerDocumentService(db).upload_from_url(
		payload=payload,
		current_customer=current_customer,
	)
	return ActionResponse(message="Document uploaded successfully")


@router.delete(
	"/{document_id}",
	response_model=ActionResponse,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Delete a customer-uploaded document",
)
def delete_document(
	document_id: uuid.UUID,
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	CustomerDocumentService(db).delete(document_id, current_customer)
	return ActionResponse(message="Document deleted successfully")
