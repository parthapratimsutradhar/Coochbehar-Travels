from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"


class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    FOLLOW_UP = "FOLLOW_UP"
    QUALIFIED = "QUALIFIED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"


class EnquiryType(str, Enum):
    FIXED_TOUR = "FIXED_TOUR"
    CUSTOM_TOUR = "CUSTOM_TOUR"
    ROOM_REQUEST = "ROOM_REQUEST"
    VEHICLE_REQUEST = "VEHICLE_REQUEST"


class EnquiryChannel(str, Enum):
    WEBSITE = "WEBSITE"
    WHATSAPP = "WHATSAPP"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    OFFLINE = "OFFLINE"
    ADMIN = "ADMIN"


class EnquiryStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    QUOTED = "QUOTED"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class LeadSource(str, Enum):
    WEBSITE = "WEBSITE"
    WHATSAPP = "WHATSAPP"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    OFFLINE = "OFFLINE"
    IMPORT = "IMPORT"
    REFERRAL = "REFERRAL"
    OTHER = "OTHER"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TourType(str, Enum):
    DOMESTIC = "DOMESTIC"
    INTERNATIONAL = "INTERNATIONAL"


class MealPlan(str, Enum):
    NONE = "NONE"
    CP = "CP"
    MAP = "MAP"
    AP = "AP"


class VehicleType(str, Enum):
    FOUR_SEATER = "4-seater"
    SIX_SEATER = "6-seater"
    TEMPO = "Tempo"
