from templar.studio.navigation import (
    DEFAULT_PAGE,
    NAVIGATION_ITEMS,
    get_navigation_item
)

def test_navigation_ids_are_unique():
    ids = [item.id for item in NAVIGATION_ITEMS]
    assert len(ids) == len(set(ids))

def test_default_page_exists():
    assert get_navigation_item(DEFAULT_PAGE).id == DEFAULT_PAGE

def test_unknown_page_falls_back_to_overview():
    assert get_navigation_item("unknown").id == DEFAULT_PAGE