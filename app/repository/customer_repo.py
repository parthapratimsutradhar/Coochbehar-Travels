import uuid
import secrets
import string
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.enums import LeadSource
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.models.visitor import Visitor


class CustomerRepository:
    """Repository for Customer data access and visitor linking operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        """Fetch customer by primary key ID."""
        stmt = select(Customer).where(Customer.id == customer_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Customer | None:
        """Fetch customer by lowercase email."""
        stmt = select(Customer).where(Customer.email.ilike(email.strip()))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_mobile(self, mobile: str) -> Customer | None:
        """Fetch customer by mobile number."""
        stmt = select(Customer).where(Customer.mobile == mobile.strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_identifier(self, identifier: str) -> Customer | None:
        """Fetch customer by email or mobile."""
        cleaned = identifier.strip()
        if "@" in cleaned:
            return self.get_by_email(cleaned)
        return self.get_by_mobile(cleaned)

    def create_customer(
        self,
        name: str = "Valued Traveler",
        mobile: str | None = None,
        email: str | None = None,
        source: LeadSource = LeadSource.WEBSITE,
        **kwargs,
    ) -> Customer:
        """Create and persist a new customer with auto-generated customer_code."""
        customer = Customer(
            customer_code=kwargs.get("customer_code") or f"CUS-{uuid.uuid4().hex[:8].upper()}",
            referral_code=kwargs.get("referral_code") or "".join(
                secrets.choice(string.ascii_letters + string.digits)
                for _ in range(8)
            ),
            name=name,
            mobile=mobile.strip() if mobile else None,
            email=email.strip().lower() if email else None,
            address=kwargs.get("address"),
            emergency_contact_name=kwargs.get("emergency_contact_name"),
            emergency_contact_mobile=kwargs.get("emergency_contact_mobile"),
            profile_pic=kwargs.get("profile_pic"),
            source=source,
            is_imported=kwargs.get("is_imported", False),
            is_active=kwargs.get("is_active", True),
        )
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def list_customers(
        self,
        page: int,
        page_size: int,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Customer], int]:
        """Fetch paginated customers with optional filters."""
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

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        customers = self.db.execute(
            stmt.order_by(Customer.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return customers, total_items

    def update_customer(
        self,
        customer: Customer,
        update_data: dict,
    ) -> Customer:
        """Update customer fields."""
        for field, value in update_data.items():
            if value is not None:
                setattr(customer, field, value)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def delete_customer(self, customer: Customer) -> None:
        """Permanently delete a customer and its configured dependents."""
        self.db.delete(customer)
        self.db.commit()

    def link_visitor_to_customer(
        self,
        customer_id: uuid.UUID,
        visitor_id: uuid.UUID,
    ) -> None:
        """Associate anonymous web visitor tracking telemetry to this customer."""
        # 1. Update visitor customer_id
        stmt_vis = (
            update(Visitor)
            .where(Visitor.id == visitor_id)
            .values(customer_id=customer_id)
        )
        self.db.execute(stmt_vis)

        # 2. Update any enquiries created by this visitor that lack customer_id
        stmt_enq = (
            update(Enquiry)
            .where(Enquiry.visitor_id == visitor_id, Enquiry.customer_id.is_(None))
            .values(customer_id=customer_id)
        )
        self.db.execute(stmt_enq)

        # 3. Update any leads created by this visitor that lack customer_id
        stmt_lead = (
            update(Lead)
            .where(Lead.visitor_id == visitor_id, Lead.customer_id.is_(None))
            .values(customer_id=customer_id)
        )
        self.db.execute(stmt_lead)
        self.db.commit()
