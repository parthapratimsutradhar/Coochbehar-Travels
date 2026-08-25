from fastapi import APIRouter

from app.api.v1.enduser.auth import router as auth_router
from app.api.v1.enduser.enquiries import router as enquiries_router
from app.api.v1.enduser.review import router as review_router
from app.api.v1.enduser.tour_packages import router as tour_packages_router
from app.api.v1.enduser.visitors import router as visitors_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(tour_packages_router)
router.include_router(enquiries_router)
router.include_router(review_router)
router.include_router(visitors_router)
