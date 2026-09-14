from enum import Enum


class AccountRole(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF" 
    CUSTOMER = "CUSTOMER"


class ActorType(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
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


class CustomerTourStatus(str, Enum):
    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    
    
class ReferralStatus(str, Enum):
    PENDING = "PENDING"
    CONVERTED = "CONVERTED"
    REWARDED = "REWARDED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"    


class DocumentType(str, Enum):
    ID_PROOF = "ID_PROOF"
    ADDRESS_PROOF = "ADDRESS_PROOF"
    TOUR_DOCUMENT = "TOUR_DOCUMENT"
    OTHER = "OTHER"    
    
    
class OfferDiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"
    
    
class OfferStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    RAZORPAY = "RAZORPAY"
    UPI = "UPI"
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    NET_BANKING = "NET_BANKING"
    CARD = "CARD"
    OFFLINE = "OFFLINE"
    OTHER = "OTHER"

class TransactionType(str, Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"  


class FinancialAccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class FinancialAccountOwnerType(str, Enum):
    SYSTEM = "SYSTEM"
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"


class FinancialTransactionType(str, Enum):
    BOOKING_PAYMENT = "BOOKING_PAYMENT"
    BOOKING_REFUND = "BOOKING_REFUND"
    WALLET_CREDIT = "WALLET_CREDIT"
    WALLET_DEBIT = "WALLET_DEBIT"
    EXPENSE = "EXPENSE"
    VENDOR_PAYMENT = "VENDOR_PAYMENT"
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"
    REFERRAL_REWARD = "REFERRAL_REWARD"


class FinancialTransactionStatus(str, Enum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REVERSED = "REVERSED"
    
class BookingStatus(str, Enum):
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    FULLY_PAID = "FULLY_PAID"
    TRAVELLED = "TRAVELLED"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"    
    
class BookingSource(str, Enum):
    APP = "APP"
    WEBSITE = "WEBSITE"
    WHATSAPP = "WHATSAPP"
    FACEBOOK = "FACEBOOK"
    INSTAGRAM = "INSTAGRAM"
    PHONE = "PHONE"
    WALK_IN = "WALK_IN"
    EXISTING_CUSTOMER = "EXISTING_CUSTOMER"
    REFERRAL = "REFERRAL"
    B2B = "B2B"
    OFFLINE = "OFFLINE"
    OTHER = "OTHER"      
    
    
class QuotationStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED" 
    
        
class QuotationItemType(str, Enum):
    HOTEL = "hotel"
    TRANSPORT = "transport"
    FLIGHT = "flight"
    TRAIN = "train"
    MEAL = "meal"
    ACTIVITY = "activity"
    GUIDE = "guide"
    PERMIT = "permit"
    TRANSFER = "transfer"
    OTHER = "other"