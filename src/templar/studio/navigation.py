from dataclasses import dataclass

@dataclass(frozen=True)
class NavigationItem:
    id: str
    label: str
    description: str

NAVIGATION_ITEMS = (
    NavigationItem(
        id="overview",
        label="Overview",
        description="Project overview"
    ),
    NavigationItem(
        id="config",
        label="Config",
        description="Application configuration"
    ),
    NavigationItem(
        id="routes",
        label="Routes",
        description="Registered application routes"
    ),
    NavigationItem(
        id="templates",
        label="Templates",
        description="Python UI templates"
    ),
    NavigationItem(
        id="requests",
        label="Requests",
        description="Request activity"
    ),
    NavigationItem(
        id="database",
        label="Database",
        description="Database configuration"
    ),
    NavigationItem(
        id="project-doctor",
        label="Project Doctor",
        description="Project diagnostics"
    )
)

DEFAULT_PAGE = "overview"

def get_navigation_item(page_id: str) -> NavigationItem:
    for item in NAVIGATION_ITEMS:
        if item.id == page_id:
            return item

    return NAVIGATION_ITEMS[0]
