from pydantic import Field
from app.schemas.base import SchemaBase


class FileUploadResponse(SchemaBase):
    url: str = Field(..., description="Secure Cloudinary URL for the uploaded file")
    public_id: str
    folder: str
    resource_type: str
    format: str | None = None
    bytes: int | None = None
