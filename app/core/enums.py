from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"


class ActorType(str, Enum):
    USER = "USER"
    CUSTOMER = "CUSTOMER"


class AdminOtpPurpose(str, Enum):
    LOGIN = "LOGIN"
    VERIFY_MOBILE = "VERIFY_MOBILE"
    VERIFY_EMAIL = "VERIFY_EMAIL"
    DELETE_ACCOUNT = "DELETE_ACCOUNT"


class CustomerOtpPurpose(str, Enum):
    LOGIN = "LOGIN"
    SIGNUP = "SIGNUP"
    VERIFY_MOBILE = "VERIFY_MOBILE"
    VERIFY_EMAIL = "VERIFY_EMAIL"
    DELETE_ACCOUNT = "DELETE_ACCOUNT"


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
    APP = "APP"
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
    ANY = "ANY"
    NONE = "NONE"
    CP = "CP"
    MAP = "MAP"
    AP = "AP"


class VehicleType(str, Enum):
    ANY = "ANY"
    NONE = "NONE"
    FOUR_SEATER = "4-seater"
    SIX_SEATER = "6-seater"
    TEMPO = "Tempo"


class OauthPurpose(str, Enum):
    ADMIN_LOGIN = "ADMIN_LOGIN"
    CUSTOMER_LOGIN = "CUSTOMER_LOGIN"
    CUSTOMER_LINK = "CUSTOMER_LINK"


class CustomerTourStatus(str, Enum):
    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"