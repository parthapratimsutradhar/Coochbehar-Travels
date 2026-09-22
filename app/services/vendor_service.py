import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.vendor import Vendor
from app.repository.vendor_repo import VendorRepository
from app.schemas.vendor import VendorCreate, VendorUpdate


class VendorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = VendorRepository(db)

    def create_vendor(self, payload: VendorCreate) -> Vendor:
        return self.repo.create(**payload.model_dump())

    def get_vendor(self, vendor_id: uuid.UUID) -> Vendor:
        vendor = self.repo.get_by_id(vendor_id)
        if not vendor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
        return vendor

    def list_vendors(
        self,
        page: int = 1,
        page_size: int = 20,
        type: str | None = None,
        search: str | None = None,
    ) -> dict:
        items, total = self.repo.list_vendors(page=page, page_size=page_size, type=type, search=search)
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
        }

    def update_vendor(self, vendor_id: uuid.UUID, payload: VendorUpdate) -> Vendor:
        vendor = self.get_vendor(vendor_id)
        return self.repo.update(vendor, payload.model_dump(exclude_unset=True))

    def delete_vendor(self, vendor_id: uuid.UUID) -> None:
        self.repo.delete(self.get_vendor(vendor_id))
