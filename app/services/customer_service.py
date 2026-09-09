import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import LeadSource
from app.models.account import Account
from app.models.booking import Booking
from app.models.document import Document
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.models.referral import Referral
from app.models.review import Review
from app.repository.booking_repo import BookingRepository
from app.repository.customer_repo import CustomerRepository
from app.repository.enquiry_repo import EnquiryRepository
from app.repository.lead_repo import LeadRepository
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
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
        self.booking_repo = BookingRepository(db)
        self.enquiry_repo = EnquiryRepository(db)
        self.lead_repo = LeadRepository(db)

    def list_customers(
        self,
        page: int,
        page_size: int,
        is_active: bool | None = None,
        search: str | None = None,
        source: LeadSource | None = None,
    ) -> dict[str, Any]:
        customers, total_items = self.repo.list_customers(
            page=page,
            page_size=page_size,
            is_active=is_active,
            search=search,
            source=source,
        )
        total_pages = (total_items + page_size - 1) // page_size if total_items else 0

        # Transform to schema-compatible dicts
        items = [self._to_customer_response(c) for c in customers]
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        }

    def _to_customer_response(self, customer: Account) -> CustomerResponse:
        profile = customer.customer_profile
        return CustomerResponse(
            id=customer.id,
            customer_code=customer.account_code,
            name=customer.name,
            email=customer.email,
            mobile=customer.mobile,
            address=profile.address if profile else None,
            emergency_contact_name=profile.emergency_contact_name if profile else None,
            emergency_contact_mobile=profile.emergency_contact_mobile if profile else None,
            profile_pic=customer.profile_pic,
            source=profile.source if profile else "WEBSITE",
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )

    def get_customer(self, customer_id: uuid.UUID) -> Account:
        customer = self.repo.get_by_id(customer_id)
        if not customer or not customer.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
        return customer

    def get_customer_response(self, customer_id: uuid.UUID) -> CustomerResponse:
        customer = self.get_customer(customer_id)
        return self._to_customer_response(customer)

    def create_customer(self, payload: CustomerCreate) -> CustomerResponse:
        email = payload.email.strip().lower() if payload.email else None
        mobile = payload.mobile.strip() if payload.mobile else None

        if email and self.repo.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A customer with this email already exists.",
            )
        if mobile and self.repo.get_by_mobile(mobile):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A customer with this mobile number already exists.",
            )

        customer = self.repo.create_customer(
            name=payload.name.strip(),
            mobile=mobile,
            email=email,
            address=payload.address.strip() if payload.address else None,
            emergency_contact_name=payload.emergency_contact_name.strip() if payload.emergency_contact_name else None,
            emergency_contact_mobile=payload.emergency_contact_mobile.strip() if payload.emergency_contact_mobile else None,
            profile_pic=payload.profile_pic,
            source=payload.source,
            is_active=payload.is_active,
        )
        return self._to_customer_response(customer)

    def update_customer(self, customer_id: uuid.UUID, payload: CustomerUpdate) -> CustomerResponse:
        customer = self.get_customer(customer_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = update_data["email"].strip().lower()
            existing = self.repo.get_by_email(update_data["email"])
            if existing and existing.id != customer_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A customer with this email already exists.",
                )

        if "mobile" in update_data and update_data["mobile"] is not None:
            update_data["mobile"] = update_data["mobile"].strip()
            existing = self.repo.get_by_mobile(update_data["mobile"])
            if existing and existing.id != customer_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A customer with this mobile number already exists.",
                )

        updated = self.repo.update_customer(customer, update_data)
        return self._to_customer_response(updated)

    def delete_customer(self, customer_id: uuid.UUID) -> None:
        customer = self.get_customer(customer_id)
        self.repo.delete_customer(customer)

    def get_customer_tab_data(
        self,
        customer_id: uuid.UUID,
        customer: Account,
        tab: str,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        if tab == "tours":
            bookings = self.booking_repo.list_for_customer(
                customer_id=customer_id,
                skip=(page - 1) * page_size,
                limit=page_size,
            )
            items = []
            for b in bookings:
                pax = b.adult_count + b.child_count + b.senior_count
                tour_name = b.package.title if b.package else f"Booking {b.booking_code}"
                destination = b.package.destination if b.package else None
                travel_date = b.departure.departure_date if b.departure else None
                items.append(
                    CustomerTourResponse(
                        id=b.id,
                        tour_name=tour_name,
                        destination=destination,
                        travel_date=travel_date,
                        return_date=None,
                        pax_no=pax,
                        total_amount=b.total_amount,
                        status=b.status.value,
                        notes=b.notes,
                        package_id=b.package_id,
                        variant_id=b.variant_id,
                        enquiry_id=b.enquiry_id,
                        created_at=b.created_at,
                        updated_at=b.updated_at,
                    ).model_dump(mode="json")
                )
            stmt_count = select(func.count()).select_from(Booking).where(Booking.customer_id == customer_id)
            total_items = self.db.execute(stmt_count).scalar_one()
        elif tab == "leads":
            stmt = select(Lead).where(Lead.customer_id == customer_id)
            total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
            records = self.db.execute(
                stmt.order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            ).scalars().all()
            items = [LeadResponse.model_validate(item).model_dump(mode="json") for item in records]
        elif tab == "enquery":
            stmt = select(Enquiry).where(Enquiry.customer_id == customer_id)
            total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
            records = self.db.execute(
                stmt.order_by(Enquiry.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            ).scalars().all()
            items = [EnquiryResponse.model_validate(item).model_dump(mode="json") for item in records]
        elif tab == "review":
            stmt = select(Review).where(Review.customer_id == customer_id, Review.is_active.is_(True))
            total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
            records = self.db.execute(
                stmt.order_by(Review.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            ).scalars().all()
            items = [ReviewResponse.model_validate(item).model_dump(mode="json") for item in records]
        elif tab == "referral":
            stmt = (
                select(Referral)
                .options(joinedload(Referral.referred_customer))
                .where(Referral.referrer_customer_id == customer_id)
            )
            total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
            records = self.db.execute(
                stmt.order_by(Referral.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            ).scalars().all()
            ref_code = customer.customer_profile.referral_code if customer.customer_profile else ""
            items = [
                ReferralHistoryItemResponse(
                    id=item.id,
                    referral_code=ref_code,
                    status=item.status,
                    reward_amount=item.reward_amount,
                    reward_issued_at=item.reward_issued_at,
                    converted_at=item.converted_at,
                    created_at=item.created_at,
                    referred_customer=item.referred_customer,
                ).model_dump(mode="json")
                for item in records
            ]
        else:  # documents
            stmt = select(Document).where(
                Document.customer_id == customer_id,
                Document.is_active.is_(True),
            )
            total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
            records = self.db.execute(
                stmt.order_by(Document.uploaded_at.desc()).offset((page - 1) * page_size).limit(page_size)
            ).scalars().all()
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
                    if item.uploaded_by_customer or item.uploaded_by_user
                    else None,
                    uploader_profile_pic=(item.uploaded_by_customer or item.uploaded_by_user).profile_pic
                    if item.uploaded_by_customer or item.uploaded_by_user
                    else None,
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
