
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ActiveEntity


class Destination(ActiveEntity):
    __tablename__ = "destinations"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    slug: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False
    )
    
    country: Mapped[str | None] = mapped_column(
        String(100)
    )
    
    description: Mapped[str | None] = mapped_column(
        Text
    )
    
    image_url: Mapped[str | None] = mapped_column(
        String(1000)
    )

    is_domestic: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=True
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False
    )

    is_popular: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False
    )
    