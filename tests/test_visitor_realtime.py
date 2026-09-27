def test_visitor_realtime_events_are_exposed():
    from app.realtime.socket_manager import REALTIME_EVENTS

    expected = {
        "visitor_connected",
        "visitor_disconnected",
        "page_view",
        "page_navigation",
        "activity",
        "click",
        "session_updated",
        "visitor_identified",
        "visitor_location_updated",
    }

    assert expected.issubset(REALTIME_EVENTS)
