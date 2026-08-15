"""Pydantic schemas for request/response serialization."""

from app.schemas.custom_tour_request import (
    CustomTourRequestCreate,
    CustomTourRequestResponse,
)
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.schemas.enquiry import EnquiryCreate, EnquiryResponse, EnquiryUpdate
from app.schemas.lead import (
    LeadActivityCreate,
    LeadActivityResponse,
    LeadCreate,
    LeadResponse,
    LeadUpdate,
)
from app.schemas.visitor import (
    VisitorCreate,
    VisitorEventCreate,
    VisitorEventResponse,
    VisitorResponse,
    VisitorSessionCreate,
    VisitorSessionResponse,
)

__all__ = [
    "CustomTourRequestCreate",
    "CustomTourRequestResponse",
    "CustomerCreate",
    "CustomerResponse",
    "CustomerUpdate",
    "EnquiryCreate",
    "EnquiryResponse",
    "EnquiryUpdate",
    "LeadActivityCreate",
    "LeadActivityResponse",
    "LeadCreate",
    "LeadResponse",
    "LeadUpdate",
    "VisitorCreate",
    "VisitorEventCreate",
    "VisitorEventResponse",
    "VisitorResponse",
    "VisitorSessionCreate",
    "VisitorSessionResponse",
]
