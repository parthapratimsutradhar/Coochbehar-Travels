import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import QuotationStatus
from app.core.messages.success import EnquirySuccess, QuotationSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.booking import BookingDetailResponse
from app.schemas.enquiry import EnquiryForQuotationResponse
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
from app.schemas.response import ActionResponse, SuccessResponse, documented_error_response
from app.services.enquiry_service import EnquiryService
from app.services.quotation_service import QuotationService


router = APIRouter(prefix="/admin/quotations", tags=["Admin - Quotations"])

AUTH_REQUIRED = documented_error_response(
	description="Missing, invalid, or expired authentication token.",
	code="UNAUTHORIZED",
	message="Authentication is required.",
)
ADMIN_ACCESS_REQUIRED = documented_error_response(
	description="The authenticated account does not have admin or staff access.",
	code="FORBIDDEN",
	message="Admin/Staff access required.",
)
INVALID_REQUEST = documented_error_response(
	description="One or more request fields failed validation.",
	code="VALIDATION_ERROR",
	message="Validation failed.",
	details=[{"field": "field_name", "message": "A valid value is required."}],
)


@router.get(
	"",
	response_model=PaginatedResponse[QuotationListResponse],
	responses={401: AUTH_REQUIRED, 403: ADMIN_ACCESS_REQUIRED},
	summary="List quotations (Admin)",
	description=(
		"Returns a paginated, newest-first list of quotations. Use `status` to filter by "
		"`DRAFT`, `SENT`, `VIEWED`, `ACCEPTED`, `REJECTED`, `EXPIRED`, or `CANCELLED`; "
		"`search` matches quotation codes and tour names; and `enquiry_id` limits results "
		"to one enquiry. Requires an authenticated admin or staff account."
	),
)
def list_quotations(
	page: int = Query(1, ge=1, description="1-based page number."),
	page_size: int = Query(20, ge=1, le=100, description="Results per page (1-100)."),
	status_filter: QuotationStatus | None = Query(None, alias="status", description="Optional quotation status filter."),
	search: str | None = Query(None, description="Search by quotation code or tour name."),
	enquiry_id: uuid.UUID | None = Query(None, description="Optional enquiry UUID."),
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> PaginatedResponse[QuotationListResponse]:
	del current_user
	result = QuotationService(db).list_all_quotations(
		page=page,
		page_size=page_size,
		status=status_filter,
		search=search,
		enquiry_id=enquiry_id,
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


@router.get(
	"/enquiries",
	response_model=PaginatedResponse[EnquiryForQuotationResponse],
	responses={401: AUTH_REQUIRED, 403: ADMIN_ACCESS_REQUIRED},
	summary="List enquiries eligible for quotations (Admin)",
	description=(
		"Returns enquiries that may receive a new quotation: those with no quotation or "
		"whose latest quotation is `REJECTED`, `EXPIRED`, or `CANCELLED`. `DRAFT`, `SENT`, "
		"`VIEWED`, and `ACCEPTED` latest quotations block creation. Enquiry status does not "
		"affect eligibility. Results are paginated and require an authenticated admin or staff account."
	),
)
def list_quotation_eligible_enquiries(
	page: int = Query(1, ge=1, description="1-based page number."),
	page_size: int = Query(100, ge=1, le=100, description="Results per page (1-100)."),
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> PaginatedResponse[EnquiryForQuotationResponse]:
	del current_user
	result = EnquiryService(db).list_quotation_eligible_enquiries(
		page=page,
		page_size=page_size,
	)
	total_pages = result["total_pages"]
	return PaginatedResponse(
		message=EnquirySuccess.RETRIEVED,
		data=[EnquiryForQuotationResponse.model_validate(item) for item in result["items"]],
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
	response_model=SuccessResponse[QuotationResponse],
	status_code=status.HTTP_201_CREATED,
	responses={
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="The referenced enquiry does not exist.",
			code="NOT_FOUND",
			message="Enquiry not found.",
		),
		409: documented_error_response(
			description="The enquiry already has a quotation that prevents creating another one.",
			code="CONFLICT",
			message="A new quotation can only be created after the latest quotation is rejected, expired, or cancelled.",
		),
		422: INVALID_REQUEST,
	},
	summary="Create a quotation (Admin)",
	description=(
		"Creates a new `DRAFT` quotation for an eligible enquiry. The quotation may be incomplete: "
		"`tour_name`, hotel details, vehicle details, cost items, and itinerary are optional. "
		"`save_as_draft` defaults to `true`; the server generates the "
		"quotation code and version, links it to the enquiry's customer where available, "
		"calculates item and total values, and leaves the enquiry status unchanged until the "
		"quotation is sent. A new quotation is allowed only when the enquiry has no quotation "
		"or the latest quotation is `REJECTED`, `EXPIRED`, or `CANCELLED`. Hotel details require "
		"a `hotel` cost item and "
		"vehicle details require a `transport` or `transfer` cost item."
	),
)
def create_quotation(
	payload: QuotationCreate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[QuotationResponse]:
	quotation = QuotationService(db).create_quotation(payload, current_user)
	return SuccessResponse(
		message=QuotationSuccess.CREATED,
		data=QuotationResponse.model_validate(quotation),
	)


@router.get(
	"/{quotation_id}",
	response_model=SuccessResponse[QuotationResponse],
	responses={
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="No quotation exists with the supplied ID.",
			code="NOT_FOUND",
			message="Quotation not found.",
		),
	},
	summary="Get a quotation (Admin)",
	description="Returns the complete quotation, including customer, package, variant, destination, cost items, hotel and vehicle details, itinerary, status timestamps, and creator information.",
)
def get_quotation(
	quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation.")],
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[QuotationResponse]:
	del current_user
	quotation = QuotationService(db).get_quotation(quotation_id)
	return SuccessResponse(message=QuotationSuccess.RETRIEVED, data=QuotationResponse.model_validate(quotation))


@router.post(
	"/{quotation_id}/versions",
	response_model=SuccessResponse[QuotationResponse],
	status_code=status.HTTP_201_CREATED,
	responses={
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="The quotation to revise does not exist.",
			code="NOT_FOUND",
			message="Quotation not found.",
		),
		409: documented_error_response(
			description="Only the latest rejected, expired, or cancelled quotation can be revised.",
			code="CONFLICT",
			message="Only the latest rejected, expired, or cancelled quotation can be revised into a new version.",
		),
		422: INVALID_REQUEST,
	},
	summary="Create a new quotation version (Admin)",
	description=(
		"Creates the next version of a quotation from the latest rejected, expired, or cancelled "
		"version. Fields omitted from the partial version payload retain values from the previous "
		"version. The supplied items replace existing items when provided; hotel and vehicle "
		"details follow the same cost-item rules as quotation creation."
	),
)
def create_quotation_version(
	quotation_id: Annotated[uuid.UUID, Path(description="UUID of the latest quotation to revise.")],
	payload: QuotationVersionCreate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[QuotationResponse]:
	quotation = QuotationService(db).create_quotation_version(quotation_id, payload, current_user)
	return SuccessResponse(
		message=QuotationSuccess.VERSION_CREATED,
		data=QuotationResponse.model_validate(quotation),
	)


@router.delete(
	"/{quotation_id}",
	response_model=ActionResponse,
	responses={
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="The quotation to delete does not exist.",
			code="NOT_FOUND",
			message="Quotation not found.",
		),
	},
	summary="Delete a quotation (Admin)",
	description="Permanently deletes the quotation and its related cost items and trip details.",
)
def delete_quotation(
	quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation.")],
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
	del current_user
	QuotationService(db).delete_quotation(quotation_id)
	return ActionResponse(message=QuotationSuccess.DELETED)


@router.patch(
	"/{quotation_id}",
	response_model=SuccessResponse[QuotationResponse],
	responses={
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="The quotation to update does not exist.",
			code="NOT_FOUND",
			message="Quotation not found.",
		),
		409: documented_error_response(
			description="The quotation has already been sent or is otherwise not editable.",
			code="CONFLICT",
			message="Quotation can only be updated before it is sent to the customer.",
		),
		422: INVALID_REQUEST,
	},
	summary="Update a quotation before it is sent to the customer (Admin)",
	description=(
		"Partially updates a `DRAFT` or `REJECTED` quotation. Omitted fields remain unchanged. "
		"When `items` is supplied, item totals are recalculated and package totals are recalculated "
		"from subtotal, discount, and tax. Hotel and vehicle arrays may be replaced independently "
		"only when matching cost items exist."
	),
)
def update_quotation(
	quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation.")],
	payload: QuotationUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[QuotationResponse]:
	quotation = QuotationService(db).update_quotation(quotation_id, payload, current_user)
	return SuccessResponse(
		message=QuotationSuccess.UPDATED,
		data=QuotationResponse.model_validate(quotation),
	)


@router.patch(
	"/{quotation_id}/status",
	response_model=ActionResponse,
	responses={
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="The quotation to update does not exist.",
			code="NOT_FOUND",
			message="Quotation not found.",
		),
		409: documented_error_response(
			description="The requested status change is not allowed for the current quotation state.",
			code="CONFLICT",
			message="The quotation cannot be moved to the requested status.",
		),
		422: INVALID_REQUEST,
	},
	summary="Update quotation status (Admin)",
	description=(
		"Admins may change `DRAFT` to `SENT` or `SENT` to `CANCELLED`. The system changes "
		"`SENT` to `VIEWED` when the customer opens the quotation and changes sent/viewed "
		"quotations to `EXPIRED` when their validity ends. Customers change quotations to "
		"`ACCEPTED` or `REJECTED`."
	),
)
def update_quotation_status(
	quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation.")],
	payload: QuotationStatusUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
	del current_user
	QuotationService(db).update_quotation_status(quotation_id, payload.status)
	return ActionResponse(message=QuotationSuccess.UPDATED)


@router.get(
	"/{quotation_id}/pdf",
	response_class=Response,
	responses={
		200: {
			"description": "Quotation PDF file.",
			"content": {
				"application/pdf": {
					"schema": {"type": "string", "format": "binary"},
				},
			},
		},
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="The quotation for the PDF does not exist.",
			code="NOT_FOUND",
			message="Quotation not found.",
		),
	},
	summary="Download a quotation PDF without hotel or vehicle details (Admin)",
	description=(
		"Generates and returns a PDF file attachment containing itinerary, general package "
		"costs, totals, inclusion/exclusion text, and terms. Hotel and vehicle details are "
		"excluded from the PDF."
	),
)
def download_quotation_pdf(
	quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation.")],
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> Response:
	del current_user
	quotation_code, pdf_content = QuotationService(db).generate_quotation_pdf(quotation_id)
	return Response(
		content=pdf_content,
		media_type="application/pdf",
		headers={
			"Content-Disposition": f'attachment; filename="{quotation_code}.pdf"',
		},
	)


@router.post(
	"/{quotation_id}/send",
	response_model=ActionResponse,
	responses={
		400: documented_error_response(
			description="The quotation could not be sent to the requested recipient.",
			code="BAD_REQUEST",
			message="The quotation email could not be sent.",
		),
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="The quotation to send does not exist.",
			code="NOT_FOUND",
			message="Quotation not found.",
		),
		409: documented_error_response(
			description="Only a draft quotation can be sent.",
			code="CONFLICT",
			message="Admins can only send draft quotations or cancel sent quotations.",
		),
		422: INVALID_REQUEST,
	},
	summary="Email a quotation to its customer (Admin)",
	description=(
		"Emails the generated quotation PDF to the supplied recipient and then changes the "
		"quotation status to `SENT`. The recipient must be a valid email address."
	),
)
async def send_quotation(
	quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation.")],
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


@router.post(
	"/{quotation_id}/convert",
	response_model=SuccessResponse[BookingDetailResponse],
	status_code=status.HTTP_201_CREATED,
	responses={
		400: documented_error_response(
			description="The quotation is not linked to a customer account and cannot be booked.",
			code="BAD_REQUEST",
			message="Quotation must be linked to a customer account before converting to a booking.",
		),
		401: AUTH_REQUIRED,
		403: ADMIN_ACCESS_REQUIRED,
		404: documented_error_response(
			description="The quotation to convert does not exist.",
			code="NOT_FOUND",
			message="Quotation not found.",
		),
		422: INVALID_REQUEST,
	},
	summary="Convert a quotation to a booking (Admin)",
	description=(
		"Converts a customer-linked quotation into an offline confirmed booking, copying "
		"quotation, package, cost-item, hotel, vehicle, and itinerary details. The quotation "
		"is marked `ACCEPTED` and its enquiry `CONVERTED`. The optional `booking_type` and "
		"`notes` fields customize the new booking."
	),
)
def convert_quotation(
	quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation to convert.")],
	payload: QuotationConvertToBookingRequest,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[BookingDetailResponse]:
	booking = QuotationService(db).convert_quotation_to_booking(
		quotation_id,
		current_user,
		booking_type=payload.booking_type,
		notes=payload.notes,
	)
	from app.services.booking_service import BookingService

	return SuccessResponse(
		message="Quotation converted to booking successfully",
		data=BookingService(db).get_booking_detail(booking.id),
	)
