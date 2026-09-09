from datetime import date
from sqlalchemy.orm import Session
from app.repository.dashboard_repo import DashboardRepository
from app.schemas.analytics import SuperAdminDashboardResponse


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DashboardRepository(db)

    def get_super_admin_dashboard(self) -> SuperAdminDashboardResponse:
        today = date.today()
        todays_metrics = self.repo.get_todays_metrics()
        future_metrics = self.repo.get_future_business_metrics()
        pipeline_metrics = self.repo.get_pipeline_metrics()
        year_overview = self.repo.get_period_overview(year=today.year)
        month_overview = self.repo.get_period_overview(year=today.year, month=today.month)

        return SuperAdminDashboardResponse(
            today=todays_metrics,
            future_business=future_metrics,
            pipeline=pipeline_metrics,
            current_year=year_overview,
            current_month=month_overview,
        )
