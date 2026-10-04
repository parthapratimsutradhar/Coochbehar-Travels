from typing import Any

from sqlalchemy import Enum, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import TourType
from app.models.base import ActiveEntity


class RuleRegulation(ActiveEntity):
    __tablename__ = "rule_regulations"

    rule_title: Mapped[str] = mapped_column(String(255), nullable=False)
    regulations: Mapped[Any] = mapped_column(JSON, nullable=False)
    type: Mapped[TourType] = mapped_column(
        Enum(TourType, native_enum=False, validate_strings=True, length=20),
        nullable=False,
        index=True,
    )