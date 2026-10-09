import uuid
from datetime import datetime

from pydantic import Field
from app.schemas.base import SchemaBase

from app.core.enums import DocumentType


class CustomerDocumentListResponse(SchemaBase):
    id: uuid.UUID
    document_type: DocumentType
    title: str
    description: str | None = None
    uploaded_by_account_id: uuid.UUID | None = None
    uploader_name: str | None = None
    uploader_profile_pic: str | None = None
    uploaded_at: datetime
    type: str
    can_delete: bool = False


class BookingDocumentListResponse(SchemaBase):
    id: uuid.UUID
    document_type: DocumentType
    booking_id: uuid.UUID
    booking_code: str
    title: str
    description: str | None = None
    uploaded_by_account_id: uuid.UUID | None = None
    uploader_name: str | None = None
    uploader_profile_pic: str | None = None
    uploaded_at: datetime
    type: str
    can_delete: bool = False


class AdminDocumentResponse(SchemaBase):
    id: uuid.UUID
    document_type: DocumentType
    title: str
    description: str | None = None
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    customer_profile_pic: str | None = None
    uploaded_by_account_id: uuid.UUID | None = None
    uploader_name: str | None = None
    uploader_profile_pic: str | None = None
    uploaded_at: datetime
    type: str
    is_active: bool
    
class AdminBookingDocumentResponse(SchemaBase):
    id: uuid.UUID
    document_type: DocumentType
    title: str
    description: str | None = None
    booking_id: uuid.UUID
    booking_code: str
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    customer_profile_pic: str | None = None
    uploaded_by_account_id: uuid.UUID | None = None
    uploader_name: str | None = None
    uploader_profile_pic: str | None = None
    uploaded_at: datetime
    type: str
    is_active: bool


class AdminDocumentUploadRequest(SchemaBase):
    customer_id: uuid.UUID | None = None
    booking_id: uuid.UUID | None = None
    file: str = Field(..., min_length=1, description="Temporary upload API URL or relative path")
    file_name: str = Field(default="document", min_length=1, max_length=255)
    document_type: DocumentType
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class CustomerDocumentUploadRequest(SchemaBase):
    file: str = Field(..., min_length=1, description="Temporary upload API URL or relative path")
    file_name: str = Field(default="document", min_length=1, max_length=255)
    document_type: DocumentType
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class DocumentUpdate(SchemaBase):
    document_type: DocumentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class BulkDeleteDocumentsRequest(SchemaBase):
    document_ids: list[uuid.UUID] = Field(..., min_length=1)


class DocumentDownloadResponse(SchemaBase):
    document_id: uuid.UUID
    file_name: str
    download_url: str