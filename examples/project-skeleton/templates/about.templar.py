"""About page template."""

import sys
sys.dont_write_bytecode = True

from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Section import Section
from templar.core.elements.Div import Div


def render(**kwargs):
    """Render about page."""
    
    content = [
        Section([
            Heading("About This Project", level=1),
            Paragraph(
                "This is a Templar Framework application. "
                "Templar is a reactive Python web framework that lets you "
                "build entire web applications using pure Python."
            ),
            
            Heading("Getting Started", level=2),
            Paragraph("To add more pages, create new .templar.py files in the templates directory."),
            
            Heading("Features", level=2),
            Div([
                Paragraph("✓ Reactive UI with Python"),
                Paragraph("✓ Built-in authentication system"),
                Paragraph("✓ Form framework with validation"),
                Paragraph("✓ Database ORM with migrations"),
                Paragraph("✓ Comprehensive logging and error handling"),
                Paragraph("✓ Performance profiling tools"),
            ], classes=["features-list"]),
            
            Heading("Learn More", level=2),
            Paragraph(
                "Visit the Templar documentation at "
                "https://github.com/Orivex-x/templar for more information."
            ),
        ], classes=["about-section"])
    ]
    
    return Main(content, id="about-page")
