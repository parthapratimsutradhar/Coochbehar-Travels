import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.messages.success import ReviewSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.schemas.review import AdminReviewCreate, AdminReviewUpdate, ReviewResponse
from app.services.review_service import ReviewService


router = APIRouter(prefix="/admin", tags=["Admin Reviews"])


@router.get(
    "/tour-packages/{tour_package_id}/reviews",
    response_model=PaginatedResponse[ReviewResponse],
    responses={404: {"model": ErrorResponse}},
    summary="List all reviews for a tour package",
)
def list_package_reviews(
    tour_package_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    is_verified: bool | None = Query(None),
    is_published: bool | None = Query(None),
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    result = ReviewService(db).list_reviews(
        tour_package_id,
        page,
        page_size,
        is_verified=is_verified,
        is_published=is_published,
    )
    return PaginatedResponse(
        message=ReviewSuccess.RETRIEVED,
        data=[
            ReviewResponse(
                id=review.id,
                package_id=review.package_id,
                customer_id=review.customer_id,
                customer_profile_picture=review.customer.profile_pic if review.customer else None,
                name=review.name,
                rating=review.rating,
                review=review.review,
                review_gallery=review.review_gallery or [],
                is_verified=review.is_verified,
                is_published=review.is_published,
                created_at=review.created_at,
            )
            for review in result["items"]
        ],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )


@router.post(
    "/tour-packages/{tour_package_id}/reviews",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Create a review for a tour package",
)
async def create_package_review(
    tour_package_id: uuid.UUID,
    payload: AdminReviewCreate,
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    await ReviewService(db).create_review(tour_package_id, payload)
    return ActionResponse(message=ReviewSuccess.CREATED)


@router.patch(
    "/reviews/{review_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Update a tour package review",
)
async def update_review(
    review_id: uuid.UUID,
    payload: AdminReviewUpdate,
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    await ReviewService(db).update_review(review_id, payload)
    return ActionResponse(message=ReviewSuccess.UPDATED)


@router.delete(
    "/reviews/{review_id}",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Delete a tour package review",
)
def delete_review(
    review_id: uuid.UUID,
    current_user: Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    ReviewService(db).delete_review(review_id)
    return ActionResponse(message=ReviewSuccess.DELETED)