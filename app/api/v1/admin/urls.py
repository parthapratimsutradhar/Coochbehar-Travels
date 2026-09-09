from fastapi import APIRouter

from app.api.v1.admin.account import router as account_router
from app.api.v1.admin.analytics import router as analytics_router
from app.api.v1.admin.auth import router as auth_router
from app.api.v1.admin.bookings import router as bookings_router
from app.api.v1.admin.customer import router as customer_router
from app.api.v1.admin.destinations import router as destinations_router
from app.api.v1.admin.documents import router as documents_router
from app.api.v1.admin.enquiries import router as enquiries_router
from app.api.v1.admin.expenses import router as expenses_router
from app.api.v1.admin.leads import router as leads_router
from app.api.v1.admin.notifications import router as notifications_router
from app.api.v1.admin.quotations import router as quotations_router
from app.api.v1.admin.tour_detail import router as tour_detail_router
from app.api.v1.admin.tour_package import router as tour_package_router
from app.api.v1.admin.tour_variant import router as tour_variant_router
from app.api.v1.admin.vendors import router as vendors_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(account_router)
router.include_router(analytics_router)
router.include_router(leads_router)
router.include_router(documents_router)
router.include_router(customer_router)
router.include_router(enquiries_router)
router.include_router(notifications_router)
router.include_router(tour_package_router)
router.include_router(tour_variant_router)
router.include_router(tour_detail_router)
router.include_router(quotations_router)
router.include_router(bookings_router)
router.include_router(destinations_router)
router.include_router(expenses_router)
router.include_router(vendors_router)
