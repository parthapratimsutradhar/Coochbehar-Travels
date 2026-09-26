import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import QuotationStatus
from app.core.messages.success import QuotationSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.quotation import (
	QuotationConvertToBookingRequest,
	QuotationCreate,
	QuotationEmailRequest,
	QuotationListResponse,
	QuotationResponse,
	QuotationStatusUpdate,
	QuotationUpdate,
	QuotationVersionCreate,
)
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.quotation_service import QuotationService


router = APIRouter(prefix="/admin/quotations", tags=["Admin - Quotations"])


@router.get(
	"",
	response_model=PaginatedResponse[QuotationListResponse],
	responses={401: {"model": ErrorResponse}},
	summary="List quotations (Admin)",
)
def list_quotations(
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	status_filter: QuotationStatus | None = Query(None, alias="status"),
	search: str | None = Query(None),
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> PaginatedResponse[QuotationListResponse]:
	del current_user
	result = QuotationService(db).list_all_quotations(
		page=page,
		page_size=page_size,
		status=status_filter,
		search=search,
	)
	total_pages = result.get("total_pages", 0)
	return PaginatedResponse(
		data=[QuotationListResponse.model_validate(item) for item in result["items"]],
		pagination=PaginationMeta(
			current_page=page,
			page_size=page_size,
			total_items=result["total_items"],
			total_pages=total_pages,
			has_next=total_pages > 0 and page < total_pages,
			has_previous=total_pages > 0 and page > 1,
		),
	)


@router.post(
	"",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Create a quotation (Admin)",
)
def create_quotation(
	payload: QuotationCreate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
	quotation = QuotationService(db).create_quotation(payload, current_user)
	return ActionResponse(message=QuotationSuccess.CREATED)


@router.get(
	"/{quotation_id}",
	response_model=SuccessResponse[QuotationResponse],
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Get a quotation (Admin)",
)
def get_quotation(
	quotation_id: uuid.UUID,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[QuotationResponse]:
	del current_user
	quotation = QuotationService(db).get_quotation(quotation_id)
	return SuccessResponse(message=QuotationSuccess.RETRIEVED, data=QuotationResponse.model_validate(quotation))


@router.post(
	"/{quotation_id}/versions",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
	summary="Create a new quotation version (Admin)",
)
def create_quotation_version(
	quotation_id: uuid.UUID,
	payload: QuotationVersionCreate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
	QuotationService(db).create_quotation_version(quotation_id, payload, current_user)
	return ActionResponse(message=QuotationSuccess.VERSION_CREATED)


@router.delete(
	"/{quotation_id}",
	response_model=ActionResponse,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Delete a quotation (Admin)",
)
def delete_quotation(
	quotation_id: uuid.UUID,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
	del current_user
	QuotationService(db).delete_quotation(quotation_id)
	return ActionResponse(message=QuotationSuccess.DELETED)


@router.patch(
	"/{quotation_id}",
	response_model=ActionResponse,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
	summary="Update a quotation before it is sent to the customer (Admin)",
)
def update_quotation(
	quotation_id: uuid.UUID,
	payload: QuotationUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
	QuotationService(db).update_quotation(quotation_id, payload, current_user)
	return ActionResponse(message=QuotationSuccess.UPDATED)


@router.patch(
	"/{quotation_id}/status",
	response_model=ActionResponse,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
	summary="Update quotation status (Admin)",
)
def update_quotation_status(
	quotation_id: uuid.UUID,
	payload: QuotationStatusUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
	del current_user
	QuotationService(db).update_quotation_status(quotation_id, payload.status)
	return ActionResponse(message=QuotationSuccess.UPDATED)


@router.get(
	"/{quotation_id}/pdf",
	response_model=SuccessResponse[dict[str, str | None]],
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Get the temporary Cloudinary quotation PDF URL (Admin)",
)
async def download_quotation_pdf(
	quotation_id: uuid.UUID,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[dict[str, str | None]]:
	del current_user
	uploaded = await QuotationService(db).generate_quotation_pdf(quotation_id)
	return SuccessResponse(
		message=QuotationSuccess.PDF_GENERATED,
		data={
			"url": uploaded.get("secure_url") or uploaded.get("url"),
			"public_id": uploaded.get("public_id"),
		},
	)


@router.post(
	"/{quotation_id}/send",
	response_model=ActionResponse,
	responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Email a quotation to its customer (Admin)",
)
async def send_quotation(
	quotation_id: uuid.UUID,
	payload: QuotationEmailRequest,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
	del current_user
	await QuotationService(db).email_quotation(
		quotation_id,
		str(payload.recipient_email),
	)
	QuotationService(db).update_quotation_status(quotation_id, QuotationStatus.SENT)
	return ActionResponse(message=QuotationSuccess.SENT)
