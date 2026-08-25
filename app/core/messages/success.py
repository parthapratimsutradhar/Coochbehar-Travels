from enum import StrEnum


class UserSuccess(StrEnum):
    RETRIEVED = "Accounts retrieved successfully."
    CREATED = "User created successfully."
    UPDATED = "User updated successfully."
    DELETED = "User deleted successfully."

class LeadSuccess(StrEnum):
    RETRIEVED = "Leads fetched successfully"
    CREATED = "Lead created successfully."
    UPDATED = "Lead updated successfully."
    DELETED = "Lead deleted successfully."

class PackageSuccess(StrEnum):
    CREATED = "Tour package created successfully."
    UPDATED = "Tour package updated successfully."
    DELETED = "Tour package deleted successfully."