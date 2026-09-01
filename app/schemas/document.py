import uuid
from datetime import datetime

from pydantic import ConfigDict
from app.schemas.base import SchemaBase

from app.core.enums import DocumentType


class DocumentResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: DocumentType
    title: str
    description: str | None = None
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    customer_profile_pic: str | None = None
    uploaded_by_customer_id: uuid.UUID | None = None
    uploaded_by_user_id: uuid.UUID | None = None
    uploader_name: str | None = None
    uploader_profile_pic: str | None = None
    uploaded_at: datetime
    file_url: str
    file_name: str
    mime_type: str | None = None
    file_size: int | None = None
    uploaded_by: str
    can_delete: bool = False
    type: str = None # "incoming" for customer uploads, "outgoing" for admin uploads


class DocumentDownloadResponse(SchemaBase):
    document_id: uuid.UUID
    file_name: str
    download_url: str