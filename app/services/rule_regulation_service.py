import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import TourType
from app.models.rule_regulation import RuleRegulation
from app.repository.rule_regulation_repo import RuleRegulationRepository
from app.schemas.rule_regulation import RuleRegulationCreate, RuleRegulationUpdate


class RuleRegulationService:
    def __init__(self, db: Session) -> None:
        self.repo = RuleRegulationRepository(db)

    def create(self, payload: RuleRegulationCreate) -> RuleRegulation:
        return self.repo.create(
            RuleRegulation(
                rule_title=payload.rule_title,
                regulations=payload.regulations,
                type=payload.type,
            )
        )

    def get(self, item_id: uuid.UUID) -> RuleRegulation:
        item = self.repo.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule or regulation not found.")
        return item

    def list_admin(
        self,
        *,
        tour_type: TourType | None = None,
        is_active: bool | None = None,
    ) -> list[RuleRegulation]:
        return self.repo.list(tour_type=tour_type, is_active=is_active)

    def list_public(self, tour_type: TourType) -> list[RuleRegulation]:
        return self.repo.list(tour_type=tour_type, is_active=True)

    def update(self, item_id: uuid.UUID, payload: RuleRegulationUpdate) -> None:
        item = self.get(item_id)
        updates = payload.model_dump(exclude_unset=True)
        if any(value is None for value in updates.values()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Updated fields cannot be null.",
            )
        for field, value in updates.items():
            setattr(item, field, value)
        self.repo.save(item)

    def deactivate(self, item_id: uuid.UUID) -> None:
        item = self.get(item_id)
        item.is_active = False
        self.repo.save(item)