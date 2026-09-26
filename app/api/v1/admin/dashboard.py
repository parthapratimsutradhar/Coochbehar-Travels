
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.db.database import get_db
from app.models.account import Account
from app.schemas.dashboard import DashboardResponse
from app.schemas.response import SuccessResponse
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/admin", tags=["Admin - Dashboard"])


@router.get(
    "/dashboard",
    response_model=SuccessResponse[DashboardResponse],
    status_code=status.HTTP_200_OK,
    summary="Get admin dashboard overview",
)
def get_dashboard(
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
):
    del current_user
    dashboard_data = DashboardService(db).get_dashboard_payload()
    return SuccessResponse(
        message="Dashboard data fetched successfully",
        data=dashboard_data,
    )
