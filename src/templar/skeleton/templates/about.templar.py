import sys
sys.dont_write_bytecode = True

from templar.core.Css import CSS
from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Section import Section
from templar.core.elements.Div import Div
from templar.core.elements import Anchor

COLORS = {
    "background": "#f8fafc",
    "surface": "#ffffff",
    "primary": "#2563eb",
    "primary_dark": "#1d4ed8",
    "heading": "#0f172a",
    "text": "#475569",
    "muted": "#64748b",
    "border": "#e2e8f0",
    "success": "#16a34a",
    "success_background": "#f0fdf4",
}

def render(**kwargs):
    page_css = CSS({
        "max-width": "1000px",
        "margin": "0 auto",
        "padding": "64px 24px",
        "box-sizing": "border-box",
        "font-family": "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "color": COLORS["text"],
        "line-height": "1.7"
    })

    intro_css = CSS({
        "margin-bottom": "48px",
        "padding": "40px",
        "background": "linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%)",
        "border-radius": "20px",
        "color": "#ffffff",
        "box-shadow": "0 16px 40px rgba(15, 23, 42, 0.12)"
    })

    intro_title_css = CSS({
        "margin": "0 0 16px",
        "font-size": "clamp(2rem, 5vw, 3rem)",
        "font-weight": "800",
        "line-height": "1.15",
        "letter-spacing": "-0.04em",
        "color": "#ffffff"
    })

    intro_text_css = CSS({
        "max-width": "720px",
        "margin": "0",
        "font-size": "1.1rem",
        "line-height": "1.8",
        "color": "#dbeafe"
    })

    section_css = CSS({
        "margin-bottom": "40px",
        "padding": "32px",
        "background": COLORS["surface"],
        "border": f"1px solid {COLORS['border']}",
        "border-radius": "16px",
        "box-shadow": "0 4px 16px rgba(15, 23, 42, 0.04)"
    })

    section_title_css = CSS({
        "margin": "0 0 16px",
        "font-size": "1.5rem",
        "font-weight": "750",
        "letter-spacing": "-0.025em",
        "color": COLORS["heading"]
    })

    paragraph_css = CSS({
        "margin": "0",
        "font-size": "1rem",
        "line-height": "1.8",
        "color": COLORS["text"]
    })

    feature_list_css = CSS({
        "display": "grid",
        "grid-template-columns": "repeat(auto-fit, minmax(240px, 1fr))",
        "gap": "14px",
        "margin-top": "24px"
    })

    feature_item_css = CSS({
        "display": "flex",
        "align-items": "flex-start",
        "gap": "12px",
        "margin": "0",
        "padding": "16px",
        "background": COLORS["success_background"],
        "border": "1px solid #dcfce7",
        "border-radius": "12px",
        "font-size": "0.95rem",
        "font-weight": "500",
        "color": "#166534"
    })

    documentation_css = CSS({
        "display": "inline-block",
        "margin-top": "20px",
        "padding": "12px 18px",
        "background": COLORS["primary"],
        "border-radius": "10px",
        "color": "#ffffff",
        "font-weight": "600",
        "text-decoration": "none",
        "transition": "background 0.2s ease"
    }).hover({
        "background": COLORS["primary_dark"]
    })

    content = [
        Section(
            [
                Heading("About Templar", level=1, css=intro_title_css),
                Paragraph(
                    "Templar is a reactive Python web framework that lets you "
                    "build entire web applications using pure Python. Create "
                    "structured, interactive experiences with a familiar "
                    "Python-first development workflow.",
                    css=intro_text_css
                ),
            ],
            classes=["about-hero"],
            css=intro_css
        ),

        Section(
            [
                Heading("About This Project", level=2, css=section_title_css),
                Paragraph(
                    "This application is built with the Templar Framework. "
                    "Its component-based approach helps keep pages organized, "
                    "reusable, and straightforward to maintain.",
                    css=paragraph_css
                ),
            ],
            classes=["about-section"],
            css=section_css
        ),

        Section(
            [
                Heading("Getting Started", level=2, css=section_title_css),
                Paragraph(
                    "To add more pages, create new .templar.py files in the "
                    "templates directory. You can compose pages from reusable "
                    "elements and customize their appearance with CSS objects.",
                    css=paragraph_css
                ),
            ],
            classes=["getting-started-section"],
            css=section_css
        ),

        Section(
            [
                Heading("Features", level=2, css=section_title_css),
                Div(
                    [
                        Paragraph("✓ Reactive UI with Python", css=feature_item_css),
                        Paragraph("✓ Built-in authentication system", css=feature_item_css),
                        Paragraph("✓ Form framework with validation", css=feature_item_css),
                        Paragraph("✓ Database ORM with migrations", css=feature_item_css),
                        Paragraph("✓ Comprehensive logging and error handling", css=feature_item_css),
                        Paragraph("✓ Performance profiling tools", css=feature_item_css),
                    ],
                    classes=["features-list"],
                    css=feature_list_css
                ),
            ],
            classes=["features-section"],
            css=section_css
        ),

        Section(
            [
                Heading("Learn More", level=2, css=section_title_css),
                Paragraph(
                    "Explore the project repository for documentation, "
                    "examples, and further information about Templar.",
                    css=paragraph_css
                ),
                Div(
                    [
                        Anchor(
                            "Explore the Templar repository →",
                            href="https://github.com/Orivex-x/templar",
                            target="_blank",
                            rel="noopener noreferrer",
                            css=documentation_css,
                        )
                    ]
                ),
            ],
            classes=["learn-more-section"],
            css=section_css,
        ),
    ]

    return Main(content, id="about-page", css=page_css)