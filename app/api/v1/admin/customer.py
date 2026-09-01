import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.db.database import get_db
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.customer_service import CustomerService


router = APIRouter(prefix="/admin/customers", tags=["Admin Customers"])


@router.get(
    "",
    response_model=PaginatedResponse[CustomerResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="List all customers",
)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = CustomerService(db)
    result = service.list_customers(page=page, page_size=page_size, is_active=is_active, search=search)
    return PaginatedResponse(
        message="Customers fetched successfully",
        data=[CustomerResponse.model_validate(customer) for customer in result["items"]],
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
    "/{customer_id}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Get customer details",
)
def get_customer(
    customer_id: uuid.UUID,
    tab: Literal["tours", "leads", "enquery", "documents", "review", "referral"] | None = Query(
        None,
        description="Customer detail tab to load",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    service = CustomerService(db)
    customer = service.get_customer(customer_id)
    if tab:
        payload = service.get_customer_tab_data(
            customer_id=customer_id,
            customer=customer,
            tab=tab,
            page=page,
            page_size=page_size,
        )
        return SuccessResponse(
            message=f"Customer {tab} fetched successfully",
            data=payload,
        )
    return SuccessResponse(message="Customer fetched successfully", data=CustomerResponse.model_validate(customer))


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Create a customer",
)
def create_customer(
    payload: CustomerCreate,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    CustomerService(db).create_customer(payload)
    return ActionResponse(message="Customer created successfully")


@router.patch(
    "/{customer_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Update a customer",
)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    CustomerService(db).update_customer(customer_id, payload)
    return ActionResponse(message="Customer updated successfully")


@router.delete(
    "/{customer_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Delete a customer",
)
def delete_customer(
    customer_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    del current_user
    CustomerService(db).delete_customer(customer_id)
    return ActionResponse(message="Customer deleted successfully")
