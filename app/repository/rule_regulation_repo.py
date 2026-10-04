import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import TourType
from app.models.rule_regulation import RuleRegulation


class RuleRegulationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, item: RuleRegulation) -> RuleRegulation:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get(self, item_id: uuid.UUID) -> RuleRegulation | None:
        return self.db.get(RuleRegulation, item_id)

    def list(
        self,
        *,
        tour_type: TourType | None = None,
        is_active: bool | None = None,
    ) -> list[RuleRegulation]:
        stmt = select(RuleRegulation)
        if tour_type is not None:
            stmt = stmt.where(RuleRegulation.type == tour_type)
        if is_active is not None:
            stmt = stmt.where(RuleRegulation.is_active.is_(is_active))
        return list(
            self.db.execute(
                stmt.order_by(RuleRegulation.type, RuleRegulation.rule_title, RuleRegulation.created_at.desc())
            ).scalars().all()
        )

    def save(self, item: RuleRegulation) -> RuleRegulation:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item