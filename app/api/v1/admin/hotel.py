import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import HotelCategory
from app.db.database import get_db
from app.models.account import Account
from app.schemas.hotel import HotelCreate, HotelResponse, HotelUpdate
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.services.hotel_service import HotelService


router = APIRouter(
	prefix="/admin/hotels",
	tags=["Admin - Hotels"],
)


@router.post(
	"",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={404: {"model": ErrorResponse}},
	summary="Create a hotel",
)
def create_hotel(
	payload: HotelCreate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	HotelService(db).create_hotel(payload)
	return ActionResponse(message="Hotel created successfully")


@router.get(
	"",
	response_model=PaginatedResponse[HotelResponse],
	summary="List hotels (Admin)",
)
def list_hotels(
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	destination_id: uuid.UUID | None = Query(None),
	category: HotelCategory | None = Query(None),
	is_active: bool | None = Query(True),
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	result = HotelService(db).list_hotels(
		page=page,
		page_size=page_size,
		destination_id=destination_id,
		category=category,
		is_active=is_active,
	)
	return PaginatedResponse(
		message="Hotels fetched successfully",
		data=[HotelResponse.model_validate(hotel) for hotel in result["items"]],
		pagination=PaginationMeta(
			current_page=result["page"],
			page_size=result["page_size"],
			total_items=result["total_items"],
			total_pages=result["total_pages"],
			has_next=result["page"] < result["total_pages"],
			has_previous=result["page"] > 1,
		),
	)


@router.patch(
	"/{hotel_id}",
	response_model=ActionResponse,
	responses={404: {"model": ErrorResponse}},
	summary="Update a hotel",
)
def update_hotel(
	hotel_id: uuid.UUID,
	payload: HotelUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	HotelService(db).update_hotel(hotel_id, payload)
	return ActionResponse(message="Hotel updated successfully")


@router.delete(
	"/{hotel_id}",
	response_model=ActionResponse,
	responses={404: {"model": ErrorResponse}},
	summary="Delete a hotel",
)
def delete_hotel(
	hotel_id: uuid.UUID,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	HotelService(db).delete_hotel(hotel_id)
	return ActionResponse(message="Hotel deleted successfully")
