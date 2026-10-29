from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state

def render_templates():
    return Div(
        [
            Heading("Templates", level=2),
            Paragraph("Inspect templates registered by this project."),
            empty_state(
                "Template inspector is not connected",
                "This page will use the existing project templates. No sample templates are being displayed."
            )
        ],
        classes=["studio-page", "studio-templates"]
    )