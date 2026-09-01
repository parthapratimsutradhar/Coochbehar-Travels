from app.core.lead_scoring import calculate_score


def test_regular_tour_view_scores_interest_category():
    assert calculate_score("tour_package_view") == 5


def test_wishlist_tour_view_gets_added_boost():
    assert calculate_score("tour_package_view", {"is_wishlist": True}) == 15
    assert calculate_score("tour_package_view", {"wishlist_count": 2}) == 9


def test_wishlist_event_names_are_mapped_and_scored():
    assert calculate_score("add_to_wishlist") == 5
    assert calculate_score("add_to_wishlist", {"wishlist_count": 3}) == 11


def test_unknown_event_keeps_default_score():
    assert calculate_score("random_event_name") == 1
