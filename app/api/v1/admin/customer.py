import secrets
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin_only
from app.db.database import get_db
from app.models.customer import Customer
from app.models.customer_tour import CustomerTour
from app.models.document import Document
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.models.referral import Referral
from app.models.review import Review
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.schemas.document import DocumentResponse
from app.schemas.enquiry import EnquiryResponse
from app.schemas.lead import LeadResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.referral import ReferralHistoryItemResponse
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.schemas.review import ReviewResponse
from app.schemas.customer_tour import CustomerTourResponse


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
    stmt = select(Customer)
    if is_active is not None:
        stmt = stmt.where(Customer.is_active.is_(is_active))
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            Customer.name.ilike(term)
            | Customer.email.ilike(term)
            | Customer.mobile.ilike(term)
            | Customer.customer_code.ilike(term)
        )

    total_items = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    customers = db.execute(
        stmt.order_by(Customer.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0

    return PaginatedResponse(
        message="Customers fetched successfully",
        data=[CustomerResponse.model_validate(customer) for customer in customers],
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
    customer = db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    if tab:
        queries = {
            "tours": select(CustomerTour).where(CustomerTour.customer_id == customer_id),
            "leads": select(Lead).where(Lead.customer_id == customer_id),
            "enquery": select(Enquiry).where(Enquiry.customer_id == customer_id),
            "documents": select(Document).where(
                Document.customer_id == customer_id,
                Document.is_active.is_(True),
            ),
            "review": select(Review).where(
                Review.customer_id == customer_id,
                Review.is_active.is_(True),
            ),
            "referral": select(Referral)
            .options(joinedload(Referral.referred_customer))
            .where(Referral.referrer_customer_id == customer_id),
        }
        stmt = queries[tab]
        order_column = Document.uploaded_at if tab == "documents" else (
            Referral.created_at if tab == "referral" else
            getattr(stmt.column_descriptions[0]["entity"], "created_at")
        )
        total_items = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        records = db.execute(
            stmt.order_by(order_column.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()

        if tab == "tours":
            items = [CustomerTourResponse.model_validate(item).model_dump(mode="json") for item in records]
        elif tab == "leads":
            items = [LeadResponse.model_validate(item).model_dump(mode="json") for item in records]
        elif tab == "enquery":
            items = [EnquiryResponse.model_validate(item).model_dump(mode="json") for item in records]
        elif tab == "review":
            items = [ReviewResponse.model_validate(item).model_dump(mode="json") for item in records]
        elif tab == "referral":
            items = [
                ReferralHistoryItemResponse(
                    id=item.id,
                    referral_code=customer.referral_code,
                    status=item.status,
                    reward_amount=item.reward_amount,
                    reward_issued_at=item.reward_issued_at,
                    converted_at=item.converted_at,
                    created_at=item.created_at,
                    referred_customer=item.referred_customer,
                ).model_dump(mode="json")
                for item in records
            ]
        else:
            items = [
                DocumentResponse(
                    **{
                        field: getattr(item, field)
                        for field in (
                            "id", "document_type", "title", "description",
                            "customer_id", "uploaded_by_customer_id", "uploaded_by_user_id",
                            "uploaded_at", "file_url", "file_name", "mime_type", "file_size",
                        )
                    },
                    customer_name=customer.name,
                    customer_profile_pic=customer.profile_pic,
                    uploader_name=(item.uploaded_by_customer or item.uploaded_by_user).name
                    if item.uploaded_by_customer or item.uploaded_by_user else None,
                    uploader_profile_pic=(item.uploaded_by_customer or item.uploaded_by_user).profile_pic
                    if item.uploaded_by_customer or item.uploaded_by_user else None,
                    uploaded_by="CUSTOMER" if item.uploaded_by_customer_id else "ADMIN",
                    can_delete=False,
                ).model_dump(mode="json")
                for item in records
            ]
        total_pages = (total_items + page_size - 1) // page_size if total_items else 0
        return SuccessResponse(
            message=f"Customer {tab} fetched successfully",
            data={
                "tab": tab,
                "items": items,
                "pagination": PaginationMeta(
                    current_page=page,
                    page_size=page_size,
                    total_items=total_items,
                    total_pages=total_pages,
                    has_next=page < total_pages,
                    has_previous=page > 1,
                ).model_dump(),
            },
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
    email = payload.email.strip().lower() if payload.email else None
    mobile = payload.mobile.strip() if payload.mobile else None

    if email and db.execute(select(Customer.id).where(Customer.email == email)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with this email already exists.")
    if mobile and db.execute(select(Customer.id).where(Customer.mobile == mobile)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with this mobile number already exists.")

    customer = Customer(
        customer_code=f"CUS-{uuid.uuid4().hex[:8].upper()}",
        referral_code="".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8)),
        name=payload.name.strip(),
        mobile=mobile,
        email=email,
        address=payload.address.strip() if payload.address else None,
        emergency_contact_name=payload.emergency_contact_name.strip() if payload.emergency_contact_name else None,
        emergency_contact_mobile=payload.emergency_contact_mobile.strip() if payload.emergency_contact_mobile else None,
        profile_pic=payload.profile_pic,
        source=payload.source,
        is_imported=payload.is_imported,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
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
    customer = db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

    update_data = payload.model_dump(exclude_unset=True)
    if "email" in update_data and update_data["email"] is not None:
        update_data["email"] = update_data["email"].strip().lower()
        if db.execute(select(Customer.id).where(Customer.email == update_data["email"], Customer.id != customer_id)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with this email already exists.")
    if "mobile" in update_data and update_data["mobile"] is not None:
        update_data["mobile"] = update_data["mobile"].strip()
        if db.execute(select(Customer.id).where(Customer.mobile == update_data["mobile"], Customer.id != customer_id)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with this mobile number already exists.")

    for field, value in update_data.items():
        if value is not None:
            setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
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
    customer = db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

    customer.is_active = False
    db.commit()
    return ActionResponse(message="Customer deleted successfully")
