from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state
from templar.cli.commands.Routes import RoutesCommand


def render_routes(cli):
    command = RoutesCommand(cli)
    rows = command.run(args=[], return_rows=True) or []

    if not rows:
        content = empty_state(
            "No routes registered",
            "No routes were found in this project's router or templates.",
        )
    else:
        header = Div(
            [
                Div("Route Pattern", classes=["routes-table-heading"]),
                Div("Template File", classes=["routes-table-heading"]),
                Div("Default", classes=["routes-table-heading"]),
                Div("Exists", classes=["routes-table-heading"]),
            ],
            classes=["routes-table-row", "routes-table-header"],
        )

        route_rows = [
            Div(
                [
                    Div(row["pattern"], classes=["routes-table-cell", "route-pattern"]),
                    Div(row["template_file"], classes=["routes-table-cell", "route-template"]),
                    Div(
                        "Yes" if row["is_default"] else "No",
                        classes=[
                            "routes-table-cell",
                            "route-flag",
                            "is-yes" if row["is_default"] else "is-no",
                        ],
                    ),
                    Div(
                        "Yes" if row["exists"] else "No",
                        classes=[
                            "routes-table-cell",
                            "route-flag",
                            "is-yes" if row["exists"] else "is-no",
                        ],
                    ),
                ],
                classes=["routes-table-row"],
            )
            for row in rows
        ]

        content = Div([header, *route_rows], classes=["routes-table"])

    return Div(
        [
            Heading("Routes", level=2),
            Paragraph("Inspect routes registered by this project."),
            content,
        ],
        classes=["studio-page", "studio-routes"],
    )