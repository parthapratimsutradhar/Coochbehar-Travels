import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.vendor import Vendor


class VendorRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, vendor_id: uuid.UUID) -> Vendor | None:
        stmt = select(Vendor).where(Vendor.id == vendor_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_code(self, vendor_code: str) -> Vendor | None:
        stmt = select(Vendor).where(Vendor.vendor_code == vendor_code)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, **kwargs) -> Vendor:
        code = kwargs.get("vendor_code") or f"VND-{uuid.uuid4().hex[:6].upper()}"
        kwargs["vendor_code"] = code
        vendor = Vendor(**kwargs)
        self.db.add(vendor)
        self.db.commit()
        self.db.refresh(vendor)
        return vendor

    def list_vendors(
        self,
        page: int = 1,
        page_size: int = 20,
        type: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Vendor], int]:
        stmt = select(Vendor)
        if type:
            stmt = stmt.where(Vendor.type.ilike(type))
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Vendor.name.ilike(term)
                | Vendor.vendor_code.ilike(term)
                | Vendor.contact.ilike(term)
            )

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        vendors = self.db.execute(
            stmt.order_by(Vendor.name.asc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(vendors), total

    def update(self, vendor: Vendor, update_data: dict) -> Vendor:
        for k, v in update_data.items():
            if v is not None:
                setattr(vendor, k, v)
        self.db.commit()
        self.db.refresh(vendor)
        return vendor
