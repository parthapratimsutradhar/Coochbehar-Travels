from fastapi import APIRouter, Query

from app.core.messages.success import EnumSuccess
from app.schemas.enum import EnumListResponse
from app.schemas.response import SuccessResponse
from app.services.enum_service import EnumService


router = APIRouter(prefix="/enums", tags=["Enums"])


@router.get(
    "",
    response_model=SuccessResponse[EnumListResponse],
    summary="List application enums",
    description="Returns all UI enum groups, with optional group and text filtering.",
)
def list_enums(
    group: str | None = Query(
        default=None,
        description=(
            "Allowed enum class name. Available groups: "
            f"{', '.join(EnumService.allowed_group_names())}"
        ),
    ),
    search: str | None = Query(default=None, min_length=1),
):
    data = EnumService().list_enums(group=group, search=search)
    return SuccessResponse(
        message=EnumSuccess.RETRIEVED,
        data=data,
    )
