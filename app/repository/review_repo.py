import uuid

from datetime import date

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import BookingStatus, EnquiryStatus
from app.models.booking import Booking
from app.models.enquiry import Enquiry
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

    def list_published_for_package(
        self,
        package_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[Review], int]:
        stmt = (
            select(Review)
            .options(joinedload(Review.customer))
            .where(
                Review.package_id == package_id,
                Review.is_published.is_(True),
                Review.is_active.is_(True),
            )
        )
        total = self.db.execute(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        ).scalar_one()
        reviews = self.db.execute(
            stmt.order_by(Review.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().unique().all()
        return list(reviews), total

    def get_customer_review(
        self,
        customer_id: uuid.UUID,
        package_id: uuid.UUID,
    ) -> Review | None:
        return self.db.execute(
            select(Review)
            .options(joinedload(Review.customer))
            .where(
                Review.customer_id == customer_id,
                Review.package_id == package_id,
                Review.is_active.is_(True),
            )
        ).scalars().first()

    def has_customer_review(self, customer_id: uuid.UUID, package_id: uuid.UUID) -> bool:
        return self.db.execute(
            select(Review.id)
            .where(
                Review.customer_id == customer_id,
                Review.package_id == package_id,
            )
            .limit(1)
        ).scalar_one_or_none() is not None

    def get_customer_owned_review(
        self,
        review_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> Review | None:
        return self.db.execute(
            select(Review).where(
                Review.id == review_id,
                Review.customer_id == customer_id,
                Review.is_active.is_(True),
            )
        ).scalar_one_or_none()

    def has_eligible_enquiry(
        self,
        customer_id: uuid.UUID,
        package_id: uuid.UUID,
        today: date,
    ) -> bool:
        eligible_enquiry = self.db.query(Enquiry.id).filter(
            Enquiry.customer_id == customer_id,
            Enquiry.package_id == package_id,
            Enquiry.status != EnquiryStatus.CANCELLED,
            or_(
                Enquiry.status == EnquiryStatus.CONVERTED,
                and_(Enquiry.travel_date.is_not(None), Enquiry.travel_date < today),
            ),
        )
        return eligible_enquiry.first() is not None

    def has_completed_customer_tour(self, customer_id: uuid.UUID, package_id: uuid.UUID) -> bool:
        return (
            self.db.query(Booking.id)
            .filter(
                Booking.customer_id == customer_id,
                Booking.package_id == package_id,
                Booking.status.in_([BookingStatus.COMPLETED, BookingStatus.TRAVELLED]),
            )
            .first()
            is not None
        )

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
