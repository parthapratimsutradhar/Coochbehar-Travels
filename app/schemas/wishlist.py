import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.enums import TourType
from app.schemas.tour_package import BannerResponse


class WishlistItemResponse(BaseModel):
    """A wishlisted package with wishlist entry metadata."""

    id: uuid.UUID
    package_id: uuid.UUID
    tour_code: str
    slug: str
    title: str
    destination: str
    type: TourType
    description: str | None = None
    season_name: str | None = None
    badge: str | None = None
    banner: BannerResponse | None = None
    is_featured: bool    
    wishlisted_at: datetime