from enum import Enum


class AppEnum(str, Enum):
    """Base class for string-backed application enums."""


class AccountRole(AppEnum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    CUSTOMER = "CUSTOMER"


class AdminOtpPurpose(AppEnum):
    LOGIN = "LOGIN"
    VERIFY_MOBILE = "VERIFY_MOBILE"
    VERIFY_EMAIL = "VERIFY_EMAIL"
    DELETE_ACCOUNT = "DELETE_ACCOUNT"


class CustomerOtpPurpose(AppEnum):
    LOGIN = "LOGIN"
    SIGNUP = "SIGNUP"
    VERIFY_MOBILE = "VERIFY_MOBILE"
    VERIFY_EMAIL = "VERIFY_EMAIL"
    DELETE_ACCOUNT = "DELETE_ACCOUNT"


class LeadStatus(AppEnum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    FOLLOW_UP = "FOLLOW_UP"
    QUALIFIED = "QUALIFIED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"


class LeadActivityType(AppEnum):
    CALL = "CALL"
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    NOTE = "NOTE"
    FOLLOW_UP = "FOLLOW_UP"
    CUSTOMER_REQUEST = "CUSTOMER_REQUEST"
    QUOTE_SENT = "QUOTE_SENT"
    QUOTE_UPDATED = "QUOTE_UPDATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    BOOKING_CREATED = "BOOKING_CREATED"


class LeadLostReason(AppEnum):
    PRICE_TOO_HIGH = "PRICE_TOO_HIGH"
    BUDGET_ISSUE = "BUDGET_ISSUE"
    TRAVEL_CANCELLED = "TRAVEL_CANCELLED"
    CHANGED_DESTINATION = "CHANGED_DESTINATION"
    BOOKED_ELSEWHERE = "BOOKED_ELSEWHERE"
    NO_RESPONSE = "NO_RESPONSE"
    DATES_UNAVAILABLE = "DATES_UNAVAILABLE"
    NOT_INTERESTED = "NOT_INTERESTED"
    DUPLICATE = "DUPLICATE"
    OTHER = "OTHER"


class EnquiryType(AppEnum):
    FIXED_TOUR = "FIXED_TOUR"
    CUSTOM_TOUR = "CUSTOM_TOUR"


class EnquiryChannel(AppEnum):
    WEBSITE = "WEBSITE"
    WHATSAPP = "WHATSAPP"
    APP = "APP"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    OFFLINE = "OFFLINE"
    ADMIN = "ADMIN"


class EnquiryStatus(AppEnum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    QUOTED = "QUOTED"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class LeadSource(AppEnum):
    WEBSITE = "WEBSITE"
    WHATSAPP = "WHATSAPP"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    OFFLINE = "OFFLINE"
    IMPORT = "IMPORT"
    REFERRAL = "REFERRAL"
    OTHER = "OTHER"
    
class LeadChannel(AppEnum):
    WHATSAPP = "WHATSAPP"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    OFFLINE = "OFFLINE"


class TourType(AppEnum):
    DOMESTIC = "DOMESTIC"
    INTERNATIONAL = "INTERNATIONAL"


class MealPlan(AppEnum):
    ANY = "ANY"
    NONE = "NONE"
    CP = "CP"
    MAP = "MAP"
    AP = "AP"


class VehicleType(AppEnum):
    ANY = "ANY"
    NONE = "NONE"
    FOUR_SEATER = "4-seater"
    SIX_SEATER = "6-seater"
    TEMPO = "Tempo"


class ReferralStatus(AppEnum):
    PENDING = "PENDING"
    REGISTERED = "REGISTERED"
    BOOKING_COMPLETED = "BOOKING_COMPLETED"
    REWARD_ELIGIBLE = "REWARD_ELIGIBLE"
    REWARD_APPROVED = "REWARD_APPROVED"
    REWARD_CREDITED = "REWARD_CREDITED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class DocumentType(AppEnum):
    ID_PROOF = "ID_PROOF"
    ADDRESS_PROOF = "ADDRESS_PROOF"
    TOUR_DOCUMENT = "TOUR_DOCUMENT"
    OTHER = "OTHER"    
    
    
class OfferDiscountType(AppEnum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"
    
    
class OfferStatus(AppEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"


class PaymentStatus(AppEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentMethod(AppEnum):
    WALLET = "WALLET"
    RAZORPAY = "RAZORPAY"
    UPI = "UPI"
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    NET_BANKING = "NET_BANKING"
    CARD = "CARD"
    OFFLINE = "OFFLINE"
    OTHER = "OTHER"

class TransactionType(AppEnum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"  


class FinancialAccountType(AppEnum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"
    LOAN = "LOAN"


class FinancialAccountOwnerType(AppEnum):
    SYSTEM = "SYSTEM"
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"


class FinancialTransactionType(AppEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class FinancialTransactionCategory(AppEnum):
    REFERRAL_INCOME = "REFERRAL_INCOME"
    BOOKING_PAYMENT = "BOOKING_PAYMENT"
    BOOKING_REFUND = "BOOKING_REFUND"
    WALLET_CREDIT = "WALLET_CREDIT"
    WALLET_DEBIT = "WALLET_DEBIT"
    VENDOR_PAYMENT = "VENDOR_PAYMENT"
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"
    REFERRAL_REWARD = "REFERRAL_REWARD"


class FinancialReportType(AppEnum):
    INCOME = "income"
    EXPENSES = "expenses"
    REFERRAL_INCOME = "referral_income"
    ALL = "all"


class FinancialExportFormat(AppEnum):
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"


class FinancialPeriod(AppEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class FinancialTransactionStatus(AppEnum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REVERSED = "REVERSED"
    
class BookingStatus(AppEnum):
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    FULLY_PAID = "FULLY_PAID"
    TRAVELLED = "TRAVELLED"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"    
    
class BookingSource(AppEnum):
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
    
    
class QuotationStatus(AppEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED" 
    
        
class CostItemType(AppEnum):
    TRANSPORT = "transport"
    FLIGHT = "flight"
    TRAIN = "train"
    ACTIVITY = "activity"
    GUIDE = "guide"
    PERMIT = "permit"
    TRANSFER = "transfer"
    OTHER = "other"
    
class HotelCategory(AppEnum):
    BUDGET = "BUDGET"
    STANDARD = "STANDARD"
    DELUXE = "DELUXE"
    LUXURY = "LUXURY"    
    
class RoomType(AppEnum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    TWIN = "TWIN"
    TRIPLE = "TRIPLE"
    FAMILY = "FAMILY"
    SUITE = "SUITE"
    DELUXE = "DELUXE"
    EXECUTIVE = "EXECUTIVE"
    PRESIDENTIAL = "PRESIDENTIAL"    
    
class Gender(AppEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"    


ALLOWED_ENUM_GROUPS = (
    "BookingSource",
    "BookingStatus",
    "DocumentType",
    "EnquiryChannel",
    "EnquiryStatus",
    "EnquiryType",
    "HotelCategory",
    "LeadActivityType",
    "LeadChannel",
    "LeadLostReason",
    "LeadSource",
    "LeadStatus",
    "MealPlan",
    "OfferDiscountType",
    "OfferStatus",
    "PaymentMethod",
    "PaymentStatus",
    "QuotationItemType",
    "QuotationStatus",
    "ReferralStatus",
    "RoomType",
    "TourType",
    "TransactionType",
    "FinancialTransactionType",
    "VehicleType",
    "Gender",
    "CostItemType"
)