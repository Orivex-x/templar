from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

def empty_state(title: str, description: str):
    return Div(
        [
            Heading(title, level=3),
            Paragraph(description)
        ],
        classes=["studio-empty-state"]
    )