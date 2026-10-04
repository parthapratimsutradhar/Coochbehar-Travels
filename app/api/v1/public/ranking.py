from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ErrorResponse
from app.schemas.tour_points import PublicUserRankingItem
from app.services.tour_points_service import DEFAULT_RANKING_PAGE_SIZE, TourPointsService
from app.utils.cdn_urls import cdn_url_for_value

router = APIRouter(prefix="/public/ranking", tags=["Public - User Ranking"])


@router.get(
    "",
    response_model=PaginatedResponse[PublicUserRankingItem],
    responses={422: {"model": ErrorResponse}},
    summary="List public customer point rankings",
    description=(
        "Returns customers ordered by current point balance. Each ranking item includes "
        "the rank, customer name, optional profile picture, and point balance."
    ),
)
def list_public_ranking(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_RANKING_PAGE_SIZE, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows, total = TourPointsService(db).list_rankings(page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(
        message="User ranking fetched successfully",
        data=[PublicUserRankingItem(
            rank=row.rank,
            customer_name=row.name,
            customer_profile_picture=(
                cdn_url_for_value(row.profile_pic) if row.profile_pic else None
            ),
            customer_joined_at=row.customer_joined_at,
            point_balance=row.points,
        ) for row in rows],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )
