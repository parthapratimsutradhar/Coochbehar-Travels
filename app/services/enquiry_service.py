import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import EnquiryChannel, EnquiryStatus, EnquiryType, LeadSource, LeadStatus
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.models.tour_package import TourPackage
from app.repository.enquiry_repo import EnquiryRepository
from app.repository.lead_repo import LeadRepository
from app.schemas.custom_tour_request import CustomTourRequestCreate
from app.schemas.enquiry import EnquiryCreate
from app.services.lead_scoring_service import LeadScoringService
from app.services.notification_service import NotificationService
from app.services.socket_service import emit_enquiry_created, emit_lead_created


class EnquiryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.enquiry_repo = EnquiryRepository(db)
        self.lead_repo = LeadRepository(db)
        self.scoring_service = LeadScoringService(db)
        self.notification_service = NotificationService(db)

    async def create_fixed_tour_enquiry(self, payload: EnquiryCreate) -> Enquiry:
        enquiry_code = f"ENQ-{uuid.uuid4().hex[:8].upper()}"
        enquiry = self.enquiry_repo.create(
            enquiry_code=enquiry_code,
            visitor_id=payload.visitor_id,
            customer_id=payload.customer_id,
            enquiry_type=EnquiryType.FIXED_TOUR,
            channel=payload.channel,
            package_id=payload.package_id,
            variant_id=payload.variant_id,
            subject=payload.subject,
            message=payload.message,
            enquirer_name=payload.name,
            enquirer_phone=payload.mobile,
        )

        initial_score = self.scoring_service.calculate_initial_score(enquiry)
        lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
        lead = self.lead_repo.create(
            lead_code=lead_code,
            enquiry_id=enquiry.id,
            customer_id=payload.customer_id,
            visitor_id=payload.visitor_id,
            full_name=payload.name or payload.subject or f"Enquiry Lead {enquiry_code}",
            mobile=payload.mobile,
            lead_score=initial_score,
            status=LeadStatus.NEW,
            source=LeadSource.WEBSITE,
            notes=payload.message,
        )

        emit_enquiry_created(enquiry)
        emit_lead_created(lead)

        package = self.db.get(TourPackage, payload.package_id) if payload.package_id else None
        tour_name = package.title if package else (payload.subject or "tour enquiry")
        enquiry_date = enquiry.created_at.isoformat() if enquiry.created_at else None

        await self.notification_service.notify_admins(
            notification_type="ENQUIRY_CREATED",
            title="New customer enquiry",
            message=f"{payload.name or 'A customer'} enquired about {tour_name} on {enquiry_date}.",
            data={
                "customer_id": str(payload.customer_id) if payload.customer_id else None,
                "customer_name": payload.name,
                "tour_name": tour_name,
                "enquiry_id": str(enquiry.id),
                "enquiry_date": enquiry_date,
            },
        )
        if payload.customer_id:
            await self.notification_service.notify_customer(
                payload.customer_id,
                notification_type="ENQUIRY_CONFIRMED",
                title="Enquiry received",
                message=f"Your enquiry about {tour_name} was received. Our team will follow up with the next steps.",
                data={"tour_name": tour_name, "enquiry_id": str(enquiry.id)},
            )
        return enquiry

    async def create_custom_tour_enquiry(self, payload: CustomTourRequestCreate) -> Enquiry:
        enquiry_code = f"ENQ-{uuid.uuid4().hex[:8].upper()}"
        adults = payload.adult_count or payload.pax_no or 1
        rooms = payload.room_count or payload.no_room or 1
        v_type = str(payload.vehicle_type) if payload.vehicle_type else None
        m_plan = str(payload.meal_plan) if payload.meal_plan else None

        enquiry = self.enquiry_repo.create(
            enquiry_code=enquiry_code,
            visitor_id=payload.visitor_id,
            customer_id=payload.customer_id,
            enquiry_type=payload.enquiry_type or EnquiryType.CUSTOM_TOUR,
            channel=payload.channel,
            subject=f"Custom Tour to {payload.destination}",
            message=payload.special_requirements,
            enquirer_name=payload.name,
            enquirer_phone=payload.mobile,
            destination=payload.destination,
            travel_date=payload.travel_date,
            travel_duration_day=payload.travel_duration_day,
            travel_duration_night=payload.travel_duration_night,
            adult_count=adults,
            child_count=payload.child_count or 0,
            senior_count=payload.senior_count or 0,
            room_count=rooms,
            vehicle_type=v_type,
            meal_plan=m_plan,
            special_requirements=payload.special_requirements,
        )

        initial_score = self.scoring_service.calculate_initial_score(enquiry)
        lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
        lead = self.lead_repo.create(
            lead_code=lead_code,
            enquiry_id=enquiry.id,
            customer_id=payload.customer_id,
            visitor_id=payload.visitor_id,
            full_name=enquiry.enquirer_name or "Custom Tour Customer",
            mobile=enquiry.enquirer_phone,
            lead_score=initial_score,
            status=LeadStatus.NEW,
            source=LeadSource.WEBSITE,
            notes=f"Custom tour request for {payload.destination} ({adults} pax, {rooms} rooms)",
        )

        emit_enquiry_created(enquiry)
        emit_lead_created(lead)

        enquiry_date = enquiry.created_at.isoformat() if enquiry.created_at else None
        tour_name = f"custom tour to {payload.destination}"
        await self.notification_service.notify_admins(
            notification_type="ENQUIRY_CREATED",
            title="New custom tour enquiry",
            message=f"{payload.name or 'A customer'} enquired about {tour_name} on {enquiry_date}.",
            data={
                "customer_id": str(payload.customer_id) if payload.customer_id else None,
                "customer_name": payload.name,
                "tour_name": tour_name,
                "enquiry_id": str(enquiry.id),
                "enquiry_date": enquiry_date,
            },
        )
        if payload.customer_id:
            await self.notification_service.notify_customer(
                payload.customer_id,
                notification_type="ENQUIRY_CONFIRMED",
                title="Enquiry received",
                message=f"Your enquiry about {tour_name} was received. Our team will follow up with the next steps.",
                data={"tour_name": tour_name, "enquiry_id": str(enquiry.id)},
            )
        return enquiry

    def list_my_enquiries(self, customer_id: uuid.UUID, skip: int = 0, limit: int = 50) -> list[Enquiry]:
        return self.enquiry_repo.list_for_customer(customer_id=customer_id, skip=skip, limit=limit)

    def list_all_enquiries(
        self,
        page: int = 1,
        page_size: int = 20,
        status: EnquiryStatus | None = None,
        search: str | None = None,
    ) -> dict:
        items, total = self.enquiry_repo.list_all(page=page, page_size=page_size, status=status, search=search)
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
        }

    def get_enquiry(self, enquiry_id: uuid.UUID) -> Enquiry:
        enquiry = self.enquiry_repo.get_by_id(enquiry_id)
        if not enquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enquiry not found.")
        return enquiry

    def update_enquiry_status(self, enquiry_id: uuid.UUID, new_status: EnquiryStatus) -> Enquiry:
        enquiry = self.get_enquiry(enquiry_id)
        return self.enquiry_repo.update_status(enquiry, new_status)
