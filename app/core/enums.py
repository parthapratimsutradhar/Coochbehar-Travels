from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"

class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    BOOKED = "BOOKED"
    LOST = "LOST"

class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class TourType(str, Enum):
    DOMESTIC = "DOMESTIC"
    INTERNATIONAL = "INTERNATIONAL"

class MealPlan(str, Enum):
    NONE = "NONE"
    CP ="CONTINENTAL PLAN, BREAKFAST ONLY"
    MAP = "MODIFIED AMERICAN PLAN, BREAKFAST AND LUNCH"
    AP = "AMERICAN PLAN, BREAKFAST, LUNCH AND DINNER"

class VehicleType(str, Enum):
    FOUR_SEATER = "4-seater"
    SIX_SEATER = "6-seater"
    TEMPO = "Tempo"     
    
class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"    
    
class BookingType(str, Enum):
    TOUR_PACKAGE = "TOUR_PACKAGE"
    CUSTOM_TOUR = "CUSTOM_TOUR"
    ROOM_BOOKING = "ROOM_BOOKING"    