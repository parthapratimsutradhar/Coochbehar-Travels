import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.core.enums import OfferStatus
from app.db.database import get_db
from app.models.account import Account
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.schemas.tour_offer import (
    TourOfferCreate,
    TourOfferResponse,
    TourOfferStatusUpdate,
    TourOfferUpdate,
)
from app.services.tour_offer_service import TourOfferService

router = APIRouter(prefix="/admin/tour-offers", tags=["Admin - Tour Offers"])


@router.post(
    "",
    response_model=SuccessResponse[TourOfferResponse],
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Create a tour offer",
)
def create_offer(
    payload: TourOfferCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    offer = TourOfferService(db).create_offer(payload)
    return SuccessResponse(message="Offer created successfully", data=TourOfferResponse.model_validate(offer))


@router.get(
    "",
    response_model=SuccessResponse[list[TourOfferResponse]],
    summary="List tour offers",
)
def list_offers(
    status: OfferStatus | None = Query(default=None),
    is_public: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    offers = TourOfferService(db).list_offers(status=status, is_public=is_public)
    return SuccessResponse(message="Offers fetched successfully", data=[TourOfferResponse.model_validate(o) for o in offers])


@router.patch(
    "/{offer_id}",
    response_model=SuccessResponse[TourOfferResponse],
    summary="Update a tour offer",
)
def update_offer(
    offer_id: uuid.UUID,
    payload: TourOfferUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    offer = TourOfferService(db).update_offer(offer_id, payload)
    return SuccessResponse(message="Offer updated successfully", data=TourOfferResponse.model_validate(offer))


@router.patch(
    "/{offer_id}/status",
    response_model=SuccessResponse[TourOfferResponse],
    summary="Update a tour offer status",
)
def update_offer_status(
    offer_id: uuid.UUID,
    payload: TourOfferStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    offer = TourOfferService(db).update_offer_status(offer_id, payload.status)
    return SuccessResponse(message="Offer status updated successfully", data=TourOfferResponse.model_validate(offer))


@router.delete(
    "/{offer_id}",
    response_model=ActionResponse,
    summary="Delete a tour offer",
)
def delete_offer(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    offer = TourOfferService(db).get_offer(offer_id)
    self_db = db
    self_db.delete(offer)
    self_db.commit()
    return ActionResponse(message="Offer deleted successfully")
