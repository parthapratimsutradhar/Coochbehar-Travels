import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.core.enums import QuotationStatus
from app.models.quotation import Quotation
from app.models.trip_items import TripItem
from app.models.trip_itinerary import TripItinerary
from app.models.trip_hotel import TripHotel
from app.models.trip_vehicle import TripVehicle


class QuotationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, quotation_id: uuid.UUID) -> Quotation | None:
        stmt = (
            select(Quotation)
            .options(
                joinedload(Quotation.items).joinedload(TripItem.hotel),
                joinedload(Quotation.items).joinedload(TripItem.vehicle),
                joinedload(Quotation.customer),
                joinedload(Quotation.enquiry),
                joinedload(Quotation.itinerary),
            )
            .where(Quotation.id == quotation_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_code(self, quotation_code: str) -> Quotation | None:
        stmt = (
            select(Quotation)
            .options(
                joinedload(Quotation.items).joinedload(TripItem.hotel),
                joinedload(Quotation.items).joinedload(TripItem.vehicle),
                joinedload(Quotation.itinerary),
            )
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
            .options(
                joinedload(Quotation.items).joinedload(TripItem.hotel),
                joinedload(Quotation.items).joinedload(TripItem.vehicle),
                joinedload(Quotation.itinerary),
            )
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
            .options(
                joinedload(Quotation.items).joinedload(TripItem.hotel),
                joinedload(Quotation.items).joinedload(TripItem.vehicle),
                joinedload(Quotation.itinerary),
            )
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
        stmt = select(Quotation).options(
            joinedload(Quotation.items).joinedload(TripItem.hotel),
            joinedload(Quotation.items).joinedload(TripItem.vehicle),
            joinedload(Quotation.itinerary),
        )
        if status is not None:
            stmt = stmt.where(Quotation.status == status)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Quotation.quotation_code.ilike(term)
                | Quotation.tour_name.ilike(term)
            )

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        quotations = self.db.execute(
            stmt.order_by(Quotation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).unique().scalars().all()
        return list(quotations), total

    def create(
        self,
        quotation_data: dict,
        items: list[dict] | None = None,
        hotels: list[dict] | None = None,
        vehicles: list[dict] | None = None,
        itinerary: list[dict] | None = None,
    ) -> Quotation:
        quotation = Quotation(**quotation_data)
        self.db.add(quotation)
        self.db.flush()

        created_items = []
        if items:
            for index, it in enumerate(items):
                q_item = TripItem(quotation_id=quotation.id, **dict(it))
                q_item.sort_order = index
                self.db.add(q_item)
                self.db.flush()
                created_items.append(q_item)
        hotel_items = [item for item in created_items if item.item_type.value == "hotel"]
        for item, hotel_data in zip(hotel_items, hotels or []):
            self.db.add(TripHotel(trip_item_id=item.id, **hotel_data))
        vehicle_items = [item for item in created_items if item.item_type.value in {"transport", "transfer"}]
        for item, vehicle_data in zip(vehicle_items, vehicles or []):
            self.db.add(TripVehicle(trip_item_id=item.id, **vehicle_data))
        if itinerary:
            for it in itinerary:
                self.db.add(TripItinerary(quotation_id=quotation.id, **it))

        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def update(
        self,
        quotation: Quotation,
        update_data: dict,
        items: list[dict] | None = None,
        hotels: list[dict] | None = None,
        vehicles: list[dict] | None = None,
        itinerary: list[dict] | None = None,
    ) -> Quotation:
        for k, v in update_data.items():
            if v is not None:
                setattr(quotation, k, v)

        if items is not None:
            for old_it in quotation.items:
                self.db.delete(old_it)
            self.db.flush()

            created_items = []
            for index, it in enumerate(items):
                q_item = TripItem(quotation_id=quotation.id, **dict(it))
                q_item.sort_order = index
                self.db.add(q_item)
                self.db.flush()
                created_items.append(q_item)

            hotel_items = [item for item in created_items if item.item_type.value == "hotel"]
            for item, hotel_data in zip(hotel_items, hotels or []):
                self.db.add(TripHotel(trip_item_id=item.id, **hotel_data))

            vehicle_items = [item for item in created_items if item.item_type.value in {"transport", "transfer"}]
            for item, vehicle_data in zip(vehicle_items, vehicles or []):
                self.db.add(TripVehicle(trip_item_id=item.id, **vehicle_data))

        if itinerary is not None:
            for old_itinerary in quotation.itinerary:
                self.db.delete(old_itinerary)
            self.db.flush()
            for it in itinerary:
                self.db.add(TripItinerary(quotation_id=quotation.id, **it))

        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def delete(self, quotation: Quotation) -> None:
        self.db.delete(quotation)
        self.db.commit()

    def update_status(self, quotation: Quotation, status: QuotationStatus) -> Quotation:
        quotation.status = status
        self.db.commit()
        self.db.refresh(quotation)
        return quotation
