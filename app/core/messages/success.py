from enum import StrEnum


class UserSuccess(StrEnum):
    RETRIEVED = "Accounts retrieved successfully."
    CREATED = "User created successfully."
    UPDATED = "User updated successfully."
    DELETED = "User deleted successfully."


class EnumSuccess(StrEnum):
    RETRIEVED = "Enums fetched successfully."

class LeadSuccess(StrEnum):
    RETRIEVED = "Leads fetched successfully"
    ACTIVITIES_RETRIEVED = "Lead activities fetched successfully"
    ACTIVITY_CREATED = "Lead activity created successfully"
    CREATED = "Lead created successfully."
    UPDATED = "Lead updated successfully."
    DELETED = "Lead deleted successfully."

class PackageSuccess(StrEnum):
    CREATED = "Tour package created successfully."
    UPDATED = "Tour package updated successfully."
    DELETED = "Tour package deleted successfully."


class TourDetailSuccess(StrEnum):
    CREATED = "Tour details created successfully"
    UPDATED = "Tour details updated successfully"
    DELETED = "Tour details deleted successfully"


class ReviewSuccess(StrEnum):
    RETRIEVED = "Package reviews fetched successfully."
    CREATED = "Review created successfully."
    UPDATED = "Review updated successfully."
    DELETED = "Review deleted successfully."


class EnquirySuccess(StrEnum):
    RETRIEVED = "Enquiries fetched successfully."
    LEAD_RETRIEVED = "Enquiry lead retrieved successfully."
    CREATED = "Enquiry created successfully."
    UPDATED = "Enquiry updated successfully."
    DELETED = "Enquiry deleted successfully."


class QuotationSuccess(StrEnum):
    RETRIEVED = "Quotations fetched successfully."
    CREATED = "Quotation created successfully."
    VERSION_CREATED = "New quotation version created successfully."
    UPDATED = "Quotation updated successfully."
    DELETED = "Quotation deleted successfully."
    PDF_GENERATED = "Quotation PDF generated successfully."
    SENT = "Quotation sent successfully."


class RoomSuccess(StrEnum):
    RETRIEVED = "Rooms fetched successfully."
    CREATED = "Room created successfully."
    UPDATED = "Room updated successfully."
    DELETED = "Room deleted successfully."


class VehicleSuccess(StrEnum):
    RETRIEVED = "Vehicles fetched successfully."
    CREATED = "Vehicle created successfully."
    UPDATED = "Vehicle updated successfully."
    DELETED = "Vehicle deleted successfully."


class VendorSuccess(StrEnum):
    RETRIEVED = "Vendors fetched successfully."
    CREATED = "Vendor created successfully."
    UPDATED = "Vendor updated successfully."
    DELETED = "Vendor deleted successfully."


class FinancialAccountSuccess(StrEnum):
    RETRIEVED = "Financial accounts fetched successfully."
    CREATED = "Financial account created successfully."
    UPDATED = "Financial account updated successfully."
    DELETED = "Financial account deleted successfully."