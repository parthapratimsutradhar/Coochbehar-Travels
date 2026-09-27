"""Centralised constants for the real-time socket layer."""

# ── Events emitted TO the client ──────────────────────────────────────
REALTIME_EVENTS = {
    # Visitor lifecycle
    "visitor_connected",
    "visitor_disconnected",
    "visitor_identified",
    "visitor_location_updated",
    # Page & behaviour
    "page_view",
    "page_navigation",
    "activity",
    "click",
    "session_updated",
    # Live stats (visitor count updates)
    "live_stats",
    # Admin presence
    "presence.updated",
}

# ── Socket rooms ──────────────────────────────────────────────────────
ADMIN_REALTIME_ROOM = "ADMIN"
ANALYTICS_REALTIME_ROOM = "analytics:live"
VISITOR_REALTIME_ROOM_PREFIX = "visitor:"
