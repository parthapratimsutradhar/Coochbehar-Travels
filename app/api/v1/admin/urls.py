from fastapi import APIRouter

from app.api.v1.admin.account import router as account_router
from app.api.v1.admin.analytics import router as analytics_router
from app.api.v1.admin.auth import router as auth_router
from app.api.v1.admin.enquiries import router as enquiries_router
from app.api.v1.admin.notifications import router as notifications_router
from app.api.v1.admin.leads import router as leads_router
from app.api.v1.admin.documents import router as documents_router
from app.api.v1.admin.tour_detail import router as tour_detail_router
from app.api.v1.admin.tour_package import router as tour_package_router
from app.api.v1.admin.tour_variant import router as tour_variant_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(account_router)
router.include_router(analytics_router)
router.include_router(leads_router)
router.include_router(documents_router)
router.include_router(enquiries_router)
router.include_router(notifications_router)
router.include_router(tour_package_router)
router.include_router(tour_variant_router)
router.include_router(tour_detail_router)
