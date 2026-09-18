import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity


class LeadRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, lead_id: uuid.UUID) -> Lead | None:
        stmt = (
            select(Lead)
            .options(joinedload(Lead.enquiry))
            .where(Lead.id == lead_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_enquiry_id(self, enquiry_id: uuid.UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.enquiry_id == enquiry_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_enquiry_id_with_activities(self, enquiry_id: uuid.UUID) -> Lead | None:
        stmt = (
            select(Lead)
            .options(joinedload(Lead.enquiry), selectinload(Lead.activities))
            .where(Lead.enquiry_id == enquiry_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_activities(
        self,
        lead_id: uuid.UUID,
        *,
        skip: int,
        limit: int,
        view: str,
        now: datetime,
    ) -> list[LeadActivity]:
        stmt = select(LeadActivity).where(LeadActivity.lead_id == lead_id)
        if view == "upcoming":
            stmt = stmt.where(LeadActivity.next_follow_up_at >= now)
        elif view == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = stmt.where(
                LeadActivity.next_follow_up_at >= start,
                LeadActivity.next_follow_up_at < start + timedelta(days=1),
            )
        elif view == "overdue":
            stmt = stmt.where(LeadActivity.next_follow_up_at < now)
        return list(
            self.db.scalars(
                stmt.order_by(LeadActivity.created_at.desc()).offset(skip).limit(limit)
            ).all()
        )

    def count_activities(
        self,
        lead_id: uuid.UUID,
        *,
        view: str,
        now: datetime,
    ) -> int:
        stmt = select(func.count()).select_from(LeadActivity).where(LeadActivity.lead_id == lead_id)
        if view == "upcoming":
            stmt = stmt.where(LeadActivity.next_follow_up_at >= now)
        elif view == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = stmt.where(
                LeadActivity.next_follow_up_at >= start,
                LeadActivity.next_follow_up_at < start + timedelta(days=1),
            )
        elif view == "overdue":
            stmt = stmt.where(LeadActivity.next_follow_up_at < now)
        return self.db.execute(stmt).scalar_one()

    def get_activity(self, activity_id: uuid.UUID, lead_id: uuid.UUID) -> LeadActivity | None:
        stmt = select(LeadActivity).where(
            LeadActivity.id == activity_id,
            LeadActivity.lead_id == lead_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_activity(self, activity: LeadActivity) -> None:
        self.db.delete(activity)

    def create(self, **kwargs) -> Lead:
        lead = Lead(**kwargs)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update(self, lead: Lead, update_data: dict) -> Lead:
        for k, v in update_data.items():
            if v is not None:
                setattr(lead, k, v)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def add_activity(self, activity: LeadActivity) -> None:
        self.db.add(activity)

    def save(self) -> None:
        self.db.commit()
