import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.messages.success import RoomSuccess
from app.core.enums import RoomType
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate
from app.services.room_service import RoomService


router = APIRouter(
	prefix="/admin/hotels/{hotel_id}/rooms",
	tags=["Admin - Rooms"],
)


@router.post(
	"",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={404: {"model": ErrorResponse}},
	summary="Add a room to a hotel",
)
def create_room(
	hotel_id: uuid.UUID,
	payload: RoomCreate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	RoomService(db).create_room(hotel_id, payload)
	return ActionResponse(message=RoomSuccess.CREATED)


@router.get(
	"",
	response_model=PaginatedResponse[RoomResponse],
	responses={404: {"model": ErrorResponse}},
	summary="List rooms for a hotel",
)
def list_rooms(
	hotel_id: uuid.UUID,
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	room_type: RoomType | None = Query(None),
	min_price: Decimal | None = Query(None, ge=0),
	max_price: Decimal | None = Query(None, ge=0),
	min_capacity: int | None = Query(None, ge=1),
	max_capacity: int | None = Query(None, ge=1),
	is_active: bool | None = Query(True),
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	result = RoomService(db).list_rooms(
		hotel_id=hotel_id,
		page=page,
		page_size=page_size,
		room_type=room_type,
		min_price=min_price,
		max_price=max_price,
		min_capacity=min_capacity,
		max_capacity=max_capacity,
		is_active=is_active,
	)
	return PaginatedResponse(
		message=RoomSuccess.RETRIEVED,
		data=[RoomResponse.model_validate(room) for room in result["items"]],
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
	"/{room_id}",
	response_model=ActionResponse,
	responses={404: {"model": ErrorResponse}},
	summary="Update a hotel room",
)
def update_room(
	hotel_id: uuid.UUID,
	room_id: uuid.UUID,
	payload: RoomUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	RoomService(db).update_room(hotel_id, room_id, payload)
	return ActionResponse(message=RoomSuccess.UPDATED)


@router.delete(
	"/{room_id}",
	response_model=ActionResponse,
	responses={404: {"model": ErrorResponse}},
	summary="Delete a hotel room",
)
def delete_room(
	hotel_id: uuid.UUID,
	room_id: uuid.UUID,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	RoomService(db).delete_room(hotel_id, room_id)
	return ActionResponse(message=RoomSuccess.DELETED)
