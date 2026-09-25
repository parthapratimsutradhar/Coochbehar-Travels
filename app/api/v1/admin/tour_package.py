import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_admin_only
from app.core.enums import TourType
from app.db.database import get_db
from app.models.account import Account
from app.schemas.admin_tour import (
    AdminTourDetailPayload,
    AdminTourPackageItem,
    AdminTourVariantItem,
    TourPackageCreateRequest,
    TourPackageUpdateRequest,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, SuccessResponse
from app.services.admin_tour_service import AdminTourService


router = APIRouter(prefix="/admin/tour-packages", tags=["Admin - Tour Packages"])


@router.get(
    "",
    response_model=PaginatedResponse[AdminTourPackageItem],
    summary="List active/inactive tour packages",
)
def list_admin_tour_packages(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    is_active: bool | None = Query(None),
    is_featured: bool | None = Query(None),
    destination_id: uuid.UUID | None = Query(None),
    type: TourType | None = Query(None, description="Filter by tour type: DOMESTIC or INTERNATIONAL"),
    search: str | None = Query(None),
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    result = service.list_packages(
        page=page,
        page_size=page_size,
        is_active=is_active,
        is_featured=is_featured,
        destination_id=destination_id,
        type=type,
        search=search,
    )
    return PaginatedResponse(
        message="Items fetched successfully",
        data=result["items"],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ActionResponse,
    summary="Create a tour package",
)
def create_admin_tour_package(
    payload: TourPackageCreateRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    payload_data = payload.model_dump()
    payload_data.pop("destination", None)
    AdminTourService(db).create_package(payload_data)
    return ActionResponse(message="Tour package created successfully")


@router.patch(
    "/{tour_package_id}",
    response_model=ActionResponse,
    summary="Update a tour package",
)
def update_admin_tour_package(
    tour_package_id: uuid.UUID,
    payload: TourPackageUpdateRequest,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    payload_data = payload.model_dump(exclude_unset=True)
    payload_data.pop("destination", None)
    AdminTourService(db).update_package(tour_package_id, payload_data)
    return ActionResponse(message="Tour package updated successfully")


@router.delete(
    "/{tour_package_id}",
    response_model=ActionResponse,
    summary="Delete a tour package",
)
def delete_admin_tour_package(
    tour_package_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    AdminTourService(db).delete_package(tour_package_id)
    return ActionResponse(message="Tour package deleted successfully")


@router.get(
    "/{tour_package_id}/variants",
    response_model=PaginatedResponse[AdminTourVariantItem],
    summary="List variants for a specific tour package",
)
def list_admin_package_variants(
    tour_package_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    service.get_package(tour_package_id)
    result = service.list_variants(tour_id=tour_package_id, page=page, page_size=page_size, is_active=is_active)
    return PaginatedResponse(
        message="Items fetched successfully",
        data=result["items"],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )


@router.get(
    "/{tour_package_id}/variants/{variant_id}",
    response_model=SuccessResponse[AdminTourDetailPayload],
    summary="Get details for a selected tour variant",
)
def get_admin_package_variant_details(
    tour_package_id: uuid.UUID,
    variant_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    service = AdminTourService(db)
    detail = service.get_package_variant_details(tour_package_id, variant_id)
    departures = service.get_variant_departures(variant_id)
    return SuccessResponse(
        message="Item fetched successfully",
        data=AdminTourService._detail_to_response(detail, tour_package_id, departures),
    )

