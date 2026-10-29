from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state

def render_database():
    return Div(
        [
            Heading("Database", level=2),
            Paragraph("Inspect database registered by this project."),
            empty_state(
                "Database is not connected",
                "This page will use the existing project database. No sample databases are being displayed."
            )
        ],
        classes=["studio-page", "studio-database"]
    )