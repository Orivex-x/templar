"""Home page template."""

import sys

sys.dont_write_bytecode = True

from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Div import Div
from templar.core.elements.Section import Section
from templar.core.components import Card, Badge
from components.task_filter import TaskFilter

def render(**kwargs):
    """Render home page."""
    tasks = [
        {"title": "Fix invoice export", "done": False},
        {"title": "Update security headers", "done": True},
        {"title": "Review onboarding flow", "done": False},
        {"title": "Ship release notes", "done": True}
    ]

    content = [
        Section([
            Heading("Welcome to Templar", level=1),
            Paragraph("Build reactive web applications with pure Python"),
            
            Div([
                Card([
                    Badge("Feature", variant="primary"),
                    Heading("Reactive UI", level=3),
                    Paragraph("Build dynamic interfaces without JavaScript"),
                ], shadow=True),
                
                Card([
                    Badge("Feature", variant="success"),
                    Heading("Python-First", level=3),
                    Paragraph("Everything is Python, from views to validation"),
                ], shadow=True),
                
                Card([
                    Badge("Feature", variant="info"),
                    Heading("Built-In Tools", level=3),
                    Paragraph("Auth, forms, validation, and ORM included"),
                ], shadow=True),
            ], classes=["cards-grid"]),

            Heading("Reactive Example", level=2),
            Paragraph("This component shows how a user-defined task filter can stay in pure Python while still behaving dynamically in the browser."),
            TaskFilter(tasks)
        ], classes=["welcome-section"])
    ]
    
    return Main(content, id="home-page")
