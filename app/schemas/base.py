from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_strings(cls, data: Any) -> Any:
        if isinstance(data, Mapping):
            normalized: dict[str, Any] = {}
            for key, value in data.items():
                normalized[key] = cls.normalize_empty_strings(value)
            return normalized

        if isinstance(data, (list, tuple, set)):
            normalized_items = [cls.normalize_empty_strings(item) for item in data]
            if not normalized_items:
                return None
            if len(normalized_items) == 1 and normalized_items[0] is None:
                return None
            return normalized_items

        if isinstance(data, str):
            stripped = data.strip()
            if stripped == "":
                return None
            return data

        return data
