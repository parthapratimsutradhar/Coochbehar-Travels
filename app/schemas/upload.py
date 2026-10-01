from pydantic import Field

from app.schemas.base import SchemaBase


class FileUploadResponse(SchemaBase):
    path: str = Field(..., description="Relative CDN path stored by the application")
    url: str = Field(..., description="Public CDN URL")
    filename: str
    content_type: str
    bytes: int