import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import DocumentType


class DocumentResponse(BaseModel):
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


class DocumentDownloadResponse(BaseModel):
    document_id: uuid.UUID
    file_name: str
    download_url: str