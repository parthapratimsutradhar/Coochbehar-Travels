from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import TourType
from app.db.database import get_db
from app.schemas.response import SuccessResponse
from app.schemas.rule_regulation import RuleRegulationResponse
from app.services.rule_regulation_service import RuleRegulationService

router = APIRouter(prefix="/rules-regulations", tags=["Rules and Regulations"])


@router.get(
    "",
    response_model=SuccessResponse[list[RuleRegulationResponse]],
    summary="List active rules and regulations by tour type",
)
def list_public_rule_regulations(
    type: Literal["dom", "int"] = Query(description="Tour type: dom for domestic or int for international."),
    db: Session = Depends(get_db),
):
    tour_type = TourType.DOMESTIC if type == "dom" else TourType.INTERNATIONAL
    items = RuleRegulationService(db).list_public(tour_type)
    return SuccessResponse(
        message="Rules and regulations fetched successfully",
        data=[RuleRegulationResponse.model_validate(item) for item in items],
    )