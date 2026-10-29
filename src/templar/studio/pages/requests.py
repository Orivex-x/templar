from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state

def render_requests():
    return Div(
        [
            Heading("Requests", level=2),
            Paragraph("Inspect requests registered by this project."),
            empty_state(
                "Request inspector is not connected",
                "This page will use the existing project requests. No sample requests are being displayed."
            )
        ],
        classes=["studio-page", "studio-requests"]
    )