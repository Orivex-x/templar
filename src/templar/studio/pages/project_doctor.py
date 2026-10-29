from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state

def render_project_doctor():
    return Div(
        [
            Heading("Project Doctor", level=2),
            Paragraph("Check the health of this project."),
            empty_state(
                "Project doctor is not connected",
                "This page will check the health of the existing project. No sample diagnostics are being displayed."
            )
        ],
        classes=["studio-page", "studio-project-doctor"]
    )