import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.core.enums import LeadStatus
from app.models.lead import Lead


class LeadRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, lead_id: uuid.UUID) -> Lead | None:
        stmt = (
            select(Lead)
            .options(joinedload(Lead.enquiry), joinedload(Lead.customer))
            .where(Lead.id == lead_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_enquiry_id(self, enquiry_id: uuid.UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.enquiry_id == enquiry_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, **kwargs) -> Lead:
        lead = Lead(**kwargs)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def list_leads(
        self,
        page: int = 1,
        page_size: int = 20,
        status: LeadStatus | None = None,
        search: str | None = None,
    ) -> tuple[list[Lead], int]:
        stmt = select(Lead).options(joinedload(Lead.enquiry), joinedload(Lead.customer))
        if status is not None:
            stmt = stmt.where(Lead.status == status)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Lead.lead_code.ilike(term)
                | Lead.full_name.ilike(term)
                | Lead.mobile.ilike(term)
                | Lead.email.ilike(term)
            )

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        leads = self.db.execute(
            stmt.order_by(Lead.lead_score.desc(), Lead.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return list(leads), total

    def update(self, lead: Lead, update_data: dict) -> Lead:
        for k, v in update_data.items():
            if v is not None:
                setattr(lead, k, v)
        self.db.commit()
        self.db.refresh(lead)
        return lead
