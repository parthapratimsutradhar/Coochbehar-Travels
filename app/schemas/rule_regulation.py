from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from app.core.enums import TourType


class RuleRegulationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rule_title: str = Field(min_length=1, max_length=255)
    regulations: JsonValue
    type: TourType


class RuleRegulationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rule_title: str | None = Field(default=None, min_length=1, max_length=255)
    regulations: JsonValue | None = None
    type: TourType | None = None
    is_active: bool | None = None


class RuleRegulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_title: str
    regulations: JsonValue
    type: TourType
    is_active: bool
    created_at: datetime
    updated_at: datetime