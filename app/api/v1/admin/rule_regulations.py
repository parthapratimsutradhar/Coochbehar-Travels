import uuid

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.core.enums import TourType
from app.db.database import get_db
from app.models.account import Account
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.schemas.rule_regulation import RuleRegulationCreate, RuleRegulationResponse, RuleRegulationUpdate
from app.services.rule_regulation_service import RuleRegulationService

router = APIRouter(prefix="/admin/rules-regulations", tags=["Admin - Rules and Regulations"])


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Create a rule or regulation",
)
def create_rule_regulation(
    payload: RuleRegulationCreate,
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    RuleRegulationService(db).create(payload)
    return ActionResponse(message="Rule or regulation created successfully")


@router.get(
    "",
    response_model=SuccessResponse[list[RuleRegulationResponse]],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="List rules and regulations",
)
def list_rule_regulations(
    tour_type: TourType | None = Query(default=None, alias="type"),
    is_active: bool | None = Query(default=None),
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    items = RuleRegulationService(db).list_admin(tour_type=tour_type, is_active=is_active)
    return SuccessResponse(
        message="Rules and regulations fetched successfully",
        data=[RuleRegulationResponse.model_validate(item) for item in items],
    )


@router.get(
    "/{item_id}",
    response_model=SuccessResponse[RuleRegulationResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get a rule or regulation",
)
def get_rule_regulation(
    item_id: uuid.UUID = Path(description="Rule or regulation record ID."),
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    item = RuleRegulationService(db).get(item_id)
    return SuccessResponse(
        message="Rule or regulation fetched successfully",
        data=RuleRegulationResponse.model_validate(item),
    )


@router.patch(
    "/{item_id}",
    response_model=ActionResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Update a rule or regulation",
)
def update_rule_regulation(
    item_id: uuid.UUID,
    payload: RuleRegulationUpdate,
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    RuleRegulationService(db).update(item_id, payload)
    return ActionResponse(message="Rule or regulation updated successfully")


@router.delete(
    "/{item_id}",
    response_model=ActionResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Deactivate a rule or regulation",
)
def delete_rule_regulation(
    item_id: uuid.UUID,
    _: Account = Depends(get_current_admin_only),
    db: Session = Depends(get_db),
):
    RuleRegulationService(db).deactivate(item_id)
    return ActionResponse(message="Rule or regulation deactivated successfully")