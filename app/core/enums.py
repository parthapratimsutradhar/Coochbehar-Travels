from enum import Enum, IntEnum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    
class ActorType(str, Enum):
    USER = "USER"
    CUSTOMER = "CUSTOMER"


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


class OauthPurpose(str, Enum):
    ADMIN_LOGIN = "ADMIN_LOGIN"
    CUSTOMER_LOGIN = "CUSTOMER_LOGIN"
    CUSTOMER_LINK = "CUSTOMER_LINK"


class StatusCode(IntEnum):
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500


class ErrorCode(str, Enum):
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"

    @classmethod
    def from_status_code(cls, status_code: int) -> "ErrorCode | str":
        return {
            StatusCode.BAD_REQUEST: cls.BAD_REQUEST,
            StatusCode.UNAUTHORIZED: cls.UNAUTHORIZED,
            StatusCode.FORBIDDEN: cls.FORBIDDEN,
            StatusCode.NOT_FOUND: cls.NOT_FOUND,
            StatusCode.CONFLICT: cls.CONFLICT,
            StatusCode.UNPROCESSABLE_ENTITY: cls.VALIDATION_ERROR,
            StatusCode.INTERNAL_SERVER_ERROR: cls.INTERNAL_SERVER_ERROR,
        }.get(status_code, "ERROR")