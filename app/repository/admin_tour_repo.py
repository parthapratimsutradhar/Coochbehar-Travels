import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.tour_detail import TourDetail
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant


class AdminTourRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_package_by_id(self, package_id: uuid.UUID) -> TourPackage | None:
        return self.db.get(TourPackage, package_id)

    def get_package_by_code_or_slug(self, tour_code: str, slug: str) -> TourPackage | None:
        return (
            self.db.query(TourPackage)
            .filter(or_(TourPackage.tour_code == tour_code, TourPackage.slug == slug))
            .first()
        )

    def get_variant_by_id(self, variant_id: uuid.UUID) -> TourVariant | None:
        return self.db.get(TourVariant, variant_id)

    def get_variant_by_slug(self, slug: str) -> TourVariant | None:
        return self.db.query(TourVariant).filter(TourVariant.slug == slug).first()

    def get_detail_by_variant_id(self, variant_id: uuid.UUID) -> TourDetail | None:
        return self.db.query(TourDetail).filter(TourDetail.variant_id == variant_id).first()

    def get_detail_by_id(self, detail_id: uuid.UUID) -> TourDetail | None:
        return self.db.get(TourDetail, detail_id)
