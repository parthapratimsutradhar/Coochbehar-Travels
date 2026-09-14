import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_only
from app.core.enums import OfferStatus
from app.db.database import get_db
from app.models.account import Account
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.schemas.booking import BookingDetailResponse
from app.schemas.tour_offer import (
    TourOfferCreate,
    TourOfferListResponse,
    TourOfferUpdate,
    TourOfferVariantResponse,
    TourOfferVariantsUpdate,
)
from app.services.booking_service import BookingService
from app.services.tour_offer_service import TourOfferService

router = APIRouter(prefix="/admin/tour-offers", tags=["Admin - Tour Offers"])


@router.post(
    "",
    response_model=ActionResponse,
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
    TourOfferService(db).create_offer(payload)
    return ActionResponse(message="Offer created successfully")


@router.get(
    "",
    response_model=SuccessResponse[list[TourOfferListResponse]],
    summary="List tour offers",
)
def list_offers(
    status: OfferStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    offers = TourOfferService(db).list_offers(status=status)
    return SuccessResponse(
        message="Offers fetched successfully",
        data=[TourOfferListResponse.model_validate(o) for o in offers],
    )


@router.patch(
    "/{offer_id}",
    response_model=ActionResponse,
    summary="Update a tour offer",
)
def update_offer(
    offer_id: uuid.UUID,
    payload: TourOfferUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    TourOfferService(db).update_offer(offer_id, payload)
    return ActionResponse(message="Offer updated successfully")


@router.get(
    "/{offer_id}/variants",
    response_model=SuccessResponse[list[TourOfferVariantResponse]],
    responses={404: {"model": ErrorResponse}},
    summary="List variants linked to a tour offer",
)
def list_offer_variants(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    offer = TourOfferService(db).get_offer(offer_id)
    variants = [link.variant for link in offer.package_links]
    return SuccessResponse(
        message="Offer variants fetched successfully",
        data=[TourOfferVariantResponse.model_validate(variant) for variant in variants],
    )


@router.patch(
    "/{offer_id}/variants",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Replace the variants linked to a tour offer",
)
def update_offer_variants(
    offer_id: uuid.UUID,
    payload: TourOfferVariantsUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    TourOfferService(db).update_variants(offer_id, payload.variant_ids)
    return ActionResponse(message="Offer variants updated successfully")


@router.get(
    "/{offer_id}/bookings",
    response_model=SuccessResponse[list[BookingDetailResponse]],
    responses={404: {"model": ErrorResponse}},
    summary="List bookings made with a tour offer",
)
def list_offer_bookings(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_only),
):
    del current_user
    bookings = TourOfferService(db).list_bookings(offer_id)
    booking_service = BookingService(db)
    return SuccessResponse(
        message="Offer bookings fetched successfully",
        data=[booking_service.get_booking_detail(booking.id) for booking in bookings],
    )


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
    TourOfferService(db).delete_offer(offer_id)
    return ActionResponse(message="Offer deleted successfully")
