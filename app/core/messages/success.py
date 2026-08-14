from enum import StrEnum


class UserSuccess(StrEnum):
    CREATED = "User created successfully."
    UPDATED = "User updated successfully."
    DELETED = "User deleted successfully."

class LeadSuccess(StrEnum):
    CREATED = "Lead created successfully."
    UPDATED = "Lead updated successfully."
    DELETED = "Lead deleted successfully."

class PackageSuccess(StrEnum):
    CREATED = "Tour package created successfully."
    UPDATED = "Tour package updated successfully."
    DELETED = "Tour package deleted successfully."