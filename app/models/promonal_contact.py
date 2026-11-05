
from sqlalchemy import  Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDEntity


class PromonalContact(UUIDEntity):
    """
    Records Contact number and email of the potential customer or existing customer for marketing purposes. This table is used to store the contact information of potential customers who have shown interest in our products or services, as well as existing customers who have opted in to receive promotional communications. 
    
    """

    __tablename__ = "promonal_contacts"


    name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    mobile: Mapped[str | None] = mapped_column(
        String(20),
        index=True,
        nullable=True,
    )
    
    email: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )