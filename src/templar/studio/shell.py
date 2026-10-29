from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.navigation import NAVIGATION_ITEMS

def build_navigation(active_page: str):
    items = []

    for item in NAVIGATION_ITEMS:
        active_class = (["studio-nav-item", "is-active"] if item.id == active_page else ["studio-nav-item"])

        items.append(
            Div(
                [
                    Heading(item.label, level=3),
                    Paragraph(item.description),
                ],
                classes=active_class
            )
        )

    return Div(
        items,
        classes=["studio-sidebar"]
    )

def build_shell(content, active_page: str):
    sidebar = build_navigation(active_page)

    main = Div(
        [content],
        # [header, content],
        classes=["studio-main"]
    )

    return Div(
        [sidebar, main],
        id="templar-studio",
        classes=["templar-studio"]
    )