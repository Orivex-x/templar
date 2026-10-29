from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state
from templar.studio.components.Panel import panel

def render_overview():
    welcome = panel(
        [
            Heading("Welcome to Templar Studio", level=2),
            Paragraph("Your Python-native development workspace."),
            Paragraph("Explore your project and access development tools from one interface")
        ]
    )

    routes = panel(
        [
            Heading("Routes", level=3),
            empty_state(
                "Route inspection is not connected",
                "Registered routes will appear here when the existing Templar router is integrated"
            )
        ]
    )

    diagnostics = panel(
        [
            Heading("Project health", level=3),
            empty_state(
                "Diagnostics are not connected",
                "Project checks will appear here when the diagnostic service is implemented"
            )
        ]
    )

    return Div(
        [
            welcome,
            Div(
                [routes, diagnostics],
                classes=["studio-card-grid"]
            ),
        ],
        classes=["studio-page" "studio-overview"]
    )