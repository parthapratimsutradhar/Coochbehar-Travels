import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.review import Review


class ReviewRepository:
    """Database access for tour package reviews."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, review_id: uuid.UUID, include_inactive: bool = False) -> Review | None:
        stmt = (
            select(Review)
            .options(joinedload(Review.customer))
            .where(Review.id == review_id)
        )
        if not include_inactive:
            stmt = stmt.where(Review.is_active.is_(True))
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_package(
        self,
        package_id: uuid.UUID,
        page: int,
        page_size: int,
        is_verified: bool | None = None,
        is_published: bool | None = None,
        include_inactive: bool = False,
    ) -> tuple[list[Review], int]:
        stmt = (
            select(Review)
            .options(joinedload(Review.customer))
            .where(Review.package_id == package_id)
        )
        if not include_inactive:
            stmt = stmt.where(Review.is_active.is_(True))
        if is_verified is not None:
            stmt = stmt.where(Review.is_verified.is_(is_verified))
        if is_published is not None:
            stmt = stmt.where(Review.is_published.is_(is_published))

        total = self.db.execute(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        ).scalar_one()
        reviews = self.db.execute(
            stmt.order_by(Review.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().unique().all()
        return list(reviews), total

    def create(self, **kwargs) -> Review:
        review = Review(**kwargs)
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def update(self, review: Review, update_data: dict) -> Review:
        for field, value in update_data.items():
            setattr(review, field, value)
        self.db.commit()
        self.db.refresh(review)
        return review

    def delete(self, review: Review) -> None:
        review.is_active = False
        review.is_published = False
        self.db.commit()
