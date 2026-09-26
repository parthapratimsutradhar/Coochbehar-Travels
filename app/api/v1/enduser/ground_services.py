import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import HotelCategory, VehicleType
from app.db.database import get_db
from app.schemas.hotel import HotelPublicResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.vehicle import VehiclePublicResponse
from app.services.hotel_service import HotelService
from app.services.vehicle_service import VehicleService

router = APIRouter(tags=["Ground Services"])


@router.get(
	"/hotels",
	response_model=PaginatedResponse[HotelPublicResponse],
	summary="List active hotels",
)
def list_hotels(
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	destination_id: uuid.UUID | None = Query(None),
	category: HotelCategory | None = Query(None),
	db: Session = Depends(get_db),
) -> PaginatedResponse[HotelPublicResponse]:
	result = HotelService(db).list_hotels(
		page=page,
		page_size=page_size,
		destination_id=destination_id,
		category=category,
		is_active=True,
	)
	total_pages = result["total_pages"]
	return PaginatedResponse(
		message="Hotels fetched successfully.",
		data=[HotelPublicResponse.model_validate(hotel) for hotel in result["items"]],
		pagination=PaginationMeta(
			current_page=page,
			page_size=page_size,
			total_items=result["total_items"],
			total_pages=total_pages,
			has_next=page < total_pages,
			has_previous=page > 1 and total_pages > 0,
		),
	)


@router.get(
	"/vehicles",
	response_model=PaginatedResponse[VehiclePublicResponse],
	summary="List active vehicles",
)
def list_vehicles(
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	vehicle_type: VehicleType | None = Query(None),
	search: str | None = Query(None),
	db: Session = Depends(get_db),
) -> PaginatedResponse[VehiclePublicResponse]:
	result = VehicleService(db).list_vehicles(
		page=page,
		page_size=page_size,
		vehicle_type=vehicle_type,
		search=search,
		is_active=True,
	)
	total_pages = result["total_pages"]
	return PaginatedResponse(
		message="Vehicles fetched successfully.",
		data=[VehiclePublicResponse.model_validate(vehicle) for vehicle in result["items"]],
		pagination=PaginationMeta(
			current_page=page,
			page_size=page_size,
			total_items=result["total_items"],
			total_pages=total_pages,
			has_next=page < total_pages,
			has_previous=page > 1 and total_pages > 0,
		),
	)
