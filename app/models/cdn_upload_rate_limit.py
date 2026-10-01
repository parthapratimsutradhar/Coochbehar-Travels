from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CDNUploadRateLimit(Base):
    __tablename__ = "cdn_upload_rate_limits"

    bucket_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)