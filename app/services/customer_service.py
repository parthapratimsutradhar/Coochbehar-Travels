import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.customer_tour import CustomerTour
from app.models.document import Document
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.models.referral import Referral
from app.models.review import Review
from app.repository.customer_repo import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.customer_tour import CustomerTourResponse
from app.schemas.document import DocumentResponse
from app.schemas.enquiry import EnquiryResponse
from app.schemas.lead import LeadResponse
from app.schemas.pagination import PaginationMeta
from app.schemas.referral import ReferralHistoryItemResponse
from app.schemas.review import ReviewResponse


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CustomerRepository(db)

    def list_customers(
        self,
        page: int,
        page_size: int,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        customers, total_items = self.repo.list_customers(
            page=page,
            page_size=page_size,
            is_active=is_active,
            search=search,
        )
        total_pages = (total_items + page_size - 1) // page_size if total_items else 0

        return {
            "items": customers,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        }

    def get_customer(self, customer_id: uuid.UUID) -> Customer:
        customer = self.repo.get_by_id(customer_id)
        if not customer or not customer.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
        return customer

    def create_customer(self, payload: CustomerCreate) -> Customer:
        email = payload.email.strip().lower() if payload.email else None
        mobile = payload.mobile.strip() if payload.mobile else None

        if email and self.repo.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with this email already exists.")
        if mobile and self.repo.get_by_mobile(mobile):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with this mobile number already exists.")

        return self.repo.create_customer(
            name=payload.name.strip(),
            mobile=mobile,
            email=email,
            address=payload.address.strip() if payload.address else None,
            emergency_contact_name=payload.emergency_contact_name.strip() if payload.emergency_contact_name else None,
            emergency_contact_mobile=payload.emergency_contact_mobile.strip() if payload.emergency_contact_mobile else None,
            profile_pic=payload.profile_pic,
            source=payload.source,
            is_imported=payload.is_imported,
            is_active=payload.is_active,
        )

    def update_customer(self, customer_id: uuid.UUID, payload: CustomerUpdate) -> Customer:
        customer = self.get_customer(customer_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = update_data["email"].strip().lower()
            if self.repo.get_by_email(update_data["email"]) and self.repo.get_by_email(update_data["email"]).id != customer_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with this email already exists.")

        if "mobile" in update_data and update_data["mobile"] is not None:
            update_data["mobile"] = update_data["mobile"].strip()
            existing = self.repo.get_by_mobile(update_data["mobile"])
            if existing and existing.id != customer_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with this mobile number already exists.")

        return self.repo.update_customer(customer, update_data)

    def delete_customer(self, customer_id: uuid.UUID) -> Customer:
        customer = self.get_customer(customer_id)
        customer.is_active = False
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def get_customer_tab_data(
        self,
        customer_id: uuid.UUID,
        customer: Customer,
        tab: str,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
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
            Referral.created_at if tab == "referral" else getattr(stmt.column_descriptions[0]["entity"], "created_at")
        )

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        records = self.db.execute(
            stmt.order_by(order_column.desc()).offset((page - 1) * page_size).limit(page_size)
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
                            "id",
                            "document_type",
                            "title",
                            "description",
                            "customer_id",
                            "uploaded_by_customer_id",
                            "uploaded_by_user_id",
                            "uploaded_at",
                            "file_url",
                            "file_name",
                            "mime_type",
                            "file_size",
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
                    type="outgoing" if item.uploaded_by_customer_id == customer.id else "incoming",
                ).model_dump(mode="json")
                for item in records
            ]

        total_pages = (total_items + page_size - 1) // page_size if total_items else 0
        return {
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
        }
