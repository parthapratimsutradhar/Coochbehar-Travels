import secrets
import string
import uuid
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.enums import AccountRole, FinancialAccountOwnerType, FinancialAccountType, LeadSource
from app.models.account import Account
from app.models.customer_profile import CustomerProfile
from app.models.enquiry import Enquiry
from app.models.financial_account import FinancialAccount
from app.models.lead import Lead
from app.models.quotation import Quotation
from app.models.visitor import Visitor


class CustomerRepository:
    """Repository for Customer (Account with role=CUSTOMER and CustomerProfile) data access."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, customer_id: uuid.UUID) -> Account | None:
        """Fetch customer by primary key ID with profile eagerly loaded."""
        stmt = (
            select(Account)
            .options(joinedload(Account.customer_profile))
            .where(Account.id == customer_id, Account.role == AccountRole.CUSTOMER)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Account | None:
        """Fetch customer by lowercase email."""
        stmt = (
            select(Account)
            .options(joinedload(Account.customer_profile))
            .where(Account.email.ilike(email.strip()), Account.role == AccountRole.CUSTOMER)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_mobile(self, mobile: str) -> Account | None:
        """Fetch customer by mobile number."""
        stmt = (
            select(Account)
            .options(joinedload(Account.customer_profile))
            .where(Account.mobile == mobile.strip(), Account.role == AccountRole.CUSTOMER)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_identifier(self, identifier: str) -> Account | None:
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
    ) -> Account:
        """Create and persist a new customer account and customer profile."""
        account_code = kwargs.get("account_code") or kwargs.get("customer_code") or f"CUS-{uuid.uuid4().hex[:8].upper()}"
        referral_code = kwargs.get("referral_code") or "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(8)
        )

        account = Account(
            account_code=account_code,
            name=name,
            mobile=mobile.strip() if mobile else None,
            email=email.strip().lower() if email else None,
            profile_pic=kwargs.get("profile_pic"),
            role=AccountRole.CUSTOMER,
            is_active=kwargs.get("is_active", True),
        )
        self.db.add(account)
        self.db.flush()

        profile = CustomerProfile(
            account_id=account.id,
            address=kwargs.get("address"),
            emergency_contact_name=kwargs.get("emergency_contact_name"),
            emergency_contact_mobile=kwargs.get("emergency_contact_mobile"),
            source=source,
            special_discount_type=kwargs.get("special_discount_type"),
            special_discount=kwargs.get("special_discount"),
            referral_code=referral_code,
        )
        self.db.add(profile)
        self.db.add(
            FinancialAccount(
                account_code=f"WALLET-{account.id.hex[:12].upper()}",
                name=f"{account.name} Wallet",
                account_type=FinancialAccountType.LIABILITY,
                owner_type=FinancialAccountOwnerType.CUSTOMER,
                owner_id=account.id,
            )
        )
        self.db.commit()
        self.db.refresh(account)
        return account

    def list_customers(
        self,
        page: int,
        page_size: int,
        is_active: bool | None = None,
        search: str | None = None,
        source: LeadSource | None = None,
    ) -> tuple[list[Account], int]:
        """Fetch paginated customers with optional filters."""
        stmt = (
            select(Account)
            .options(joinedload(Account.customer_profile))
            .where(Account.role == AccountRole.CUSTOMER)
        )
        if is_active is not None:
            stmt = stmt.where(Account.is_active == is_active)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Account.name.ilike(term)
                | Account.email.ilike(term)
                | Account.mobile.ilike(term)
                | Account.account_code.ilike(term)
            )
        if source is not None:
            stmt = stmt.where(Account.customer_profile.has(CustomerProfile.source == source))

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        customers = self.db.execute(
            stmt.order_by(Account.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(customers), total_items

    def update_customer(
        self,
        customer: Account,
        update_data: dict,
    ) -> Account:
        """Update customer account and profile fields."""
        account_fields = {"name", "email", "mobile", "profile_pic", "is_active"}
        profile_fields = {
            "address",
            "emergency_contact_name",
            "emergency_contact_mobile",
            "source",
            "special_discount_type",
            "special_discount",
        }

        for field, value in update_data.items():
            if value is not None:
                if field in account_fields:
                    setattr(customer, field, value)
                elif field in profile_fields:
                    if customer.customer_profile:
                        setattr(customer.customer_profile, field, value)

        self.db.commit()
        self.db.refresh(customer)
        return customer

    def delete_customer(self, customer: Account) -> None:
        """Deactivate or delete customer."""
        customer.is_active = False
        self.db.commit()
        self.db.refresh(customer)

    def link_visitor_to_customer(
        self,
        customer_id: uuid.UUID,
        visitor_id: uuid.UUID,
    ) -> None:
        """Associate anonymous web visitor tracking telemetry to this customer."""
        stmt_vis = (
            update(Visitor)
            .where(Visitor.id == visitor_id)
            .values(customer_id=customer_id)
        )
        self.db.execute(stmt_vis)

        stmt_enq = (
            update(Enquiry)
            .where(Enquiry.visitor_id == visitor_id, Enquiry.customer_id.is_(None))
            .values(customer_id=customer_id)
        )
        self.db.execute(stmt_enq)

        self.db.commit()

    def link_identifier_records_to_customer(self, customer: Account) -> None:
        """Link anonymous enquiry history after mobile/email authentication."""
        conditions = []
        if customer.mobile:
            conditions.append(Enquiry.enquirer_phone == customer.mobile)
        if customer.email:
            conditions.append(Enquiry.enquirer_email == customer.email.lower())
        if not conditions:
            return

        enquiry_ids = list(
            self.db.scalars(
                select(Enquiry.id).where(Enquiry.customer_id.is_(None), or_(*conditions))
            ).all()
        )
        if not enquiry_ids:
            return

        self.db.execute(
            update(Enquiry).where(Enquiry.id.in_(enquiry_ids)).values(customer_id=customer.id)
        )
        self.db.execute(
            update(Quotation)
            .where(Quotation.enquiry_id.in_(enquiry_ids), Quotation.customer_id.is_(None))
            .values(customer_id=customer.id)
        )
        self.db.commit()
