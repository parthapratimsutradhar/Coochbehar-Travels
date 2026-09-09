import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.core.enums import QuotationStatus
from app.models.quotation import Quotation
from app.models.quotation_item import QuotationItem


class QuotationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, quotation_id: uuid.UUID) -> Quotation | None:
        stmt = (
            select(Quotation)
            .options(
                joinedload(Quotation.items),
                joinedload(Quotation.customer),
                joinedload(Quotation.package),
                joinedload(Quotation.variant),
                joinedload(Quotation.enquiry),
            )
            .where(Quotation.id == quotation_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_code(self, quotation_code: str) -> Quotation | None:
        stmt = (
            select(Quotation)
            .options(joinedload(Quotation.items))
            .where(Quotation.quotation_code == quotation_code)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_latest_version(self, enquiry_id: uuid.UUID) -> int:
        stmt = select(func.max(Quotation.version)).where(Quotation.enquiry_id == enquiry_id)
        max_v = self.db.execute(stmt).scalar_one_or_none()
        return max_v or 0

    def list_for_enquiry(self, enquiry_id: uuid.UUID) -> list[Quotation]:
        stmt = (
            select(Quotation)
            .options(joinedload(Quotation.items))
            .where(Quotation.enquiry_id == enquiry_id)
            .order_by(Quotation.version.desc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_for_customer(
        self,
        customer_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Quotation]:
        stmt = (
            select(Quotation)
            .options(joinedload(Quotation.items))
            .where(Quotation.customer_id == customer_id)
            .order_by(Quotation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: QuotationStatus | None = None,
        search: str | None = None,
    ) -> tuple[list[Quotation], int]:
        stmt = select(Quotation).options(joinedload(Quotation.items))
        if status is not None:
            stmt = stmt.where(Quotation.status == status)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Quotation.quotation_code.ilike(term)
                | Quotation.tour_name.ilike(term)
                | Quotation.destination.ilike(term)
            )

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        quotations = self.db.execute(
            stmt.order_by(Quotation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).unique().scalars().all()
        return list(quotations), total

    def create(self, quotation_data: dict, items: list[dict] | None = None) -> Quotation:
        quotation = Quotation(**quotation_data)
        self.db.add(quotation)
        self.db.flush()

        if items:
            for it in items:
                q_item = QuotationItem(quotation_id=quotation.id, **it)
                self.db.add(q_item)

        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def update(self, quotation: Quotation, update_data: dict, items: list[dict] | None = None) -> Quotation:
        for k, v in update_data.items():
            if v is not None:
                setattr(quotation, k, v)

        if items is not None:
            # remove old items and add new items
            for old_it in quotation.items:
                self.db.delete(old_it)
            self.db.flush()
            for it in items:
                q_item = QuotationItem(quotation_id=quotation.id, **it)
                self.db.add(q_item)

        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def update_status(self, quotation: Quotation, status: QuotationStatus) -> Quotation:
        quotation.status = status
        self.db.commit()
        self.db.refresh(quotation)
        return quotation
