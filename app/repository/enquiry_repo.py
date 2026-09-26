import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.core.enums import EnquiryStatus
from app.models.enquiry import Enquiry


class EnquiryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, enquiry_id: uuid.UUID) -> Enquiry | None:
        stmt = (
            select(Enquiry)
            .options(
                joinedload(Enquiry.package),
                joinedload(Enquiry.variant),
                joinedload(Enquiry.customer),
                joinedload(Enquiry.lead),
            )
            .where(Enquiry.id == enquiry_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_code(self, enquiry_code: str) -> Enquiry | None:
        stmt = select(Enquiry).where(Enquiry.enquiry_code == enquiry_code)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, **kwargs) -> Enquiry:
        enquiry = Enquiry(**kwargs)
        self.db.add(enquiry)
        self.db.commit()
        self.db.refresh(enquiry)
        return enquiry

    def list_for_customer(
        self,
        customer_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Enquiry]:
        stmt = (
            select(Enquiry)
            .options(
                joinedload(Enquiry.package),
                joinedload(Enquiry.variant),
                joinedload(Enquiry.lead),
            )
            .where(Enquiry.customer_id == customer_id)
            .order_by(Enquiry.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: EnquiryStatus | None = None,
        search: str | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> tuple[list[Enquiry], int]:
        stmt = select(Enquiry).options(
            joinedload(Enquiry.package),
            joinedload(Enquiry.variant),
            joinedload(Enquiry.customer),
            joinedload(Enquiry.lead),
        )
        if customer_id is not None:
            stmt = stmt.where(Enquiry.customer_id == customer_id)
        if status is not None:
            stmt = stmt.where(Enquiry.status == status)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Enquiry.enquiry_code.ilike(term)
                | Enquiry.enquirer_name.ilike(term)
                | Enquiry.enquirer_phone.ilike(term)
                | Enquiry.enquirer_email.ilike(term)
                | Enquiry.message.ilike(term)
            )

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        enquiries = self.db.execute(
            stmt.order_by(Enquiry.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(enquiries), total

    def update_status(self, enquiry: Enquiry, new_status: EnquiryStatus) -> Enquiry:
        enquiry.status = new_status
        self.db.commit()
        self.db.refresh(enquiry)
        return enquiry

    def update(self, enquiry: Enquiry, **fields) -> Enquiry:
        for field, value in fields.items():
            setattr(enquiry, field, value)
        self.db.commit()
        self.db.refresh(enquiry)
        return enquiry
