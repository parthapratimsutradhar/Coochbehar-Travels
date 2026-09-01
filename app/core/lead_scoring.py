"""Lead scoring engine — maps event types to weighted scores.

Each visitor interaction earns a lead-score delta based on its category.
Higher-intent actions (enquiry submit, booking) earn substantially more
than passive page views, producing a meaningful prioritisation signal
for the sales pipeline.
"""

from enum import Enum


class EventCategory(str, Enum):
    PAGE_VIEW = "PAGE_VIEW"
    ENGAGEMENT = "ENGAGEMENT"
    INTEREST = "INTEREST"
    INTENT = "INTENT"
    CONVERSION = "CONVERSION"
    IDENTITY = "IDENTITY"


# ── Score weights per category ────────────────────────────────────────
CATEGORY_SCORES: dict[EventCategory, int] = {
    EventCategory.PAGE_VIEW: 1,
    EventCategory.ENGAGEMENT: 2,
    EventCategory.INTEREST: 5,
    EventCategory.INTENT: 10,
    EventCategory.CONVERSION: 25,
    EventCategory.IDENTITY: 15,
}

# ── Event name → category mapping ────────────────────────────────────
EVENT_CATEGORY_MAP: dict[str, EventCategory] = {
    # Page views
    "page_view": EventCategory.PAGE_VIEW,
    "session_start": EventCategory.PAGE_VIEW,

    # Engagement signals
    "scroll_depth_50": EventCategory.ENGAGEMENT,
    "scroll_depth_75": EventCategory.ENGAGEMENT,
    "scroll_depth_100": EventCategory.ENGAGEMENT,
    "time_on_page_30s": EventCategory.ENGAGEMENT,
    "time_on_page_60s": EventCategory.ENGAGEMENT,
    "video_play": EventCategory.ENGAGEMENT,

    # Interest indicators
    "tour_package_view": EventCategory.INTEREST,
    "tour_variant_view": EventCategory.INTEREST,
    "gallery_view": EventCategory.INTEREST,
    "itinerary_view": EventCategory.INTEREST,
    "review_read": EventCategory.INTEREST,
    "compare_packages": EventCategory.INTEREST,
    "wishlist_add": EventCategory.INTEREST,
    "wishlist_remove": EventCategory.ENGAGEMENT,
    "tour_wishlist_add": EventCategory.INTEREST,
    "tour_wishlist_remove": EventCategory.ENGAGEMENT,
    "add_to_wishlist": EventCategory.INTEREST,
    "remove_from_wishlist": EventCategory.ENGAGEMENT,

    # Intent signals
    "enquiry_form_open": EventCategory.INTENT,
    "enquiry_form_fill": EventCategory.INTENT,
    "price_check": EventCategory.INTENT,
    "date_check": EventCategory.INTENT,
    "whatsapp_click": EventCategory.INTENT,
    "phone_click": EventCategory.INTENT,

    # Conversion events
    "enquiry_submit": EventCategory.CONVERSION,
    "booking_enquiry": EventCategory.CONVERSION,
    "custom_tour_request": EventCategory.CONVERSION,

    # Identity events
    "login": EventCategory.IDENTITY,
    "signup": EventCategory.IDENTITY,
    "google_oauth": EventCategory.IDENTITY,
}

# Default score for unrecognised event names
DEFAULT_EVENT_SCORE: int = 1


def _wishlist_bonus(metadata: dict | None) -> int:
    """Boost score when a tour is saved to a customer's wishlist."""
    if not isinstance(metadata, dict):
        return 0

    is_wishlist = metadata.get("is_wishlist")
    if is_wishlist is True or str(metadata.get("wishlist_status", "")).lower() in {
        "wishlisted",
        "saved",
        "in_wishlist",
    }:
        return 10

    if metadata.get("package_wishlisted") is True:
        return 10

    wishlist_count = metadata.get("wishlist_count")
    if wishlist_count is not None:
        try:
            count = int(wishlist_count)
        except (TypeError, ValueError):
            return 0
        return min(10, max(count, 0) * 2)

    return 0


def get_event_category(event_name: str) -> EventCategory | None:
    """Resolve an event name to its scoring category, or None if unknown."""
    return EVENT_CATEGORY_MAP.get(event_name.lower().strip())


def calculate_score(event_name: str, metadata: dict | None = None) -> int:
    """Return the lead-score delta for a given event.

    Parameters
    ----------
    event_name:
        The canonical event identifier (e.g. ``"tour_package_view"``).
    metadata:
        Optional event metadata — reserved for future per-event
        score modifiers (e.g. high-value package viewed → bonus).

    Returns
    -------
    int
        Positive integer score increment.
    """
    category = get_event_category(event_name)
    if category is None:
        return DEFAULT_EVENT_SCORE

    score = CATEGORY_SCORES[category]
    if category in {EventCategory.INTEREST, EventCategory.INTENT, EventCategory.CONVERSION}:
        score += _wishlist_bonus(metadata)
    return score
