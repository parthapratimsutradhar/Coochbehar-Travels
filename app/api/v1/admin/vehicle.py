import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import VehicleType
from app.core.messages.success import VehicleSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.vehicle_service import VehicleService


router = APIRouter(
	prefix="/admin/vehicles",
	tags=["Admin - Vehicles"],
)


@router.post(
	"",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={404: {"model": ErrorResponse}},
	summary="Add a vehicle",
)
def create_vehicle(
	payload: VehicleCreate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	VehicleService(db).create_vehicle(payload)
	return ActionResponse(message=VehicleSuccess.CREATED)


@router.get(
	"",
	response_model=PaginatedResponse[VehicleResponse],
	summary="List vehicles",
)
def list_vehicles(
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	vehicle_type: VehicleType | None = Query(None),
	search: str | None = Query(None),
	is_active: bool | None = Query(True),
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	result = VehicleService(db).list_vehicles(
		page=page,
		page_size=page_size,
		vehicle_type=vehicle_type,
		search=search,
		is_active=is_active,
	)
	return PaginatedResponse(
		message=VehicleSuccess.RETRIEVED,
		data=[VehicleResponse.model_validate(vehicle) for vehicle in result["items"]],
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
	"/{vehicle_id}",
	response_model=ActionResponse,
	responses={404: {"model": ErrorResponse}},
	summary="Update a vehicle",
)
def update_vehicle(
	vehicle_id: uuid.UUID,
	payload: VehicleUpdate,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	VehicleService(db).update_vehicle(vehicle_id, payload)
	return ActionResponse(message=VehicleSuccess.UPDATED)


@router.delete(
	"/{vehicle_id}",
	response_model=ActionResponse,
	responses={404: {"model": ErrorResponse}},
	summary="Delete a vehicle",
)
def delete_vehicle(
	vehicle_id: uuid.UUID,
	db: Session = Depends(get_db),
	current_user: Account = Depends(get_current_admin_or_staff),
):
	VehicleService(db).delete_vehicle(vehicle_id)
	return ActionResponse(message=VehicleSuccess.DELETED)
