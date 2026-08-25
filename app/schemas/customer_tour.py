from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import CustomerTourStatus


class CustomerTourResponse(BaseModel):
    id: UUID
    tour_name: str
    destination: str | None = None
    travel_date: date | None = None
    return_date: date | None = None
    pax_no: int | None = None
    total_amount: Decimal | None = None
    status: CustomerTourStatus
    notes: str | None = None
    package_id: UUID | None = None
    variant_id: UUID | None = None
    enquiry_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)