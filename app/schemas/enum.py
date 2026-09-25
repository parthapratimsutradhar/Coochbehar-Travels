from pydantic import BaseModel


class EnumOption(BaseModel):
    value: str
    label: str


class EnumGroup(BaseModel):
    name: str
    label: str
    options: list[EnumOption]


class EnumListResponse(BaseModel):
    groups: list[EnumGroup]
