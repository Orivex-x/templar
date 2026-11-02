from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state
from templar.studio.components.Panel import panel
from templar.cli.commands.Routes import RoutesCommand


def render_overview(cli=None):
    welcome = panel(
        [
            Heading("Welcome to Templar Studio", level=2),
            Paragraph("Your Python-native development workspace."),
            Paragraph(
                "Explore your project and access development tools from one interface."
            ),
        ]
    )

    # Routes panel
    if cli is not None:
        command = RoutesCommand(cli)
        route_rows = command.run(args=[], return_rows=True) or []

        if route_rows:
            routes_count_placeholder_text = "route" if len(route_rows) == 1 else "routes"

            route_content = Paragraph(f"{len(route_rows)} registered {routes_count_placeholder_text} found.")
        else:
            route_content = empty_state(
                "No routes registered",
                "No routes were found in this project's router or templates.",
            )
    else:
        route_content = empty_state(
            "Route inspection unavailable",
            "A CLI instance is required to inspect this project's routes.",
        )

    routes = panel(
        [
            Heading("Routes", level=3),
            route_content,
        ]
    )

    # Project diagnostics panel
    diagnostics = panel(
        [
            Heading("Project health", level=3),
            empty_state(
                "Diagnostics are not connected",
                "Project checks will appear here when the diagnostic service is implemented.",
            ),
        ]
    )

    return Div(
        [
            welcome,
            Div(
                [routes, diagnostics],
                classes=["studio-card-grid"],
            ),
        ],
        classes=["studio-page", "studio-overview"],
    )