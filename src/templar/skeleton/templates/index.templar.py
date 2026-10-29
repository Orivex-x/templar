import sys

sys.dont_write_bytecode = True

from templar.core.Css import CSS
from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Div import Div
from templar.core.elements.Section import Section
from templar.core.components import Card
from components.task_filter import TaskFilter

COLORS = {
    "background": "#f8fafc",
    "surface": "#ffffff",
    "surface_muted": "#f1f5f9",
    "text": "#0f172a",
    "text_muted": "#64748b",
    "border": "#e2e8f0",
    "primary": "#4f46e5",
    "primary_hover": "#4338ca",
    "primary_soft": "#eef2ff",
    "success": "#059669",
    "info": "#0284c7",
    "hero": "#0f172a",
    "hero_text": "#f8fafc",
    "hero_muted": "#cbd5e1"
}

FONT = "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

def render(**kwargs):
    tasks = [
        {"title": "Fix invoice export", "done": False},
        {"title": "Update security headers", "done": True},
        {"title": "Review onboarding flow", "done": False},
        {"title": "Ship release notes", "done": True}
    ]

    hero = Section(
        [
            Div(
                "Templar / Developer Platform",
                css=CSS({
                    "display": "inline-flex",
                    "align-items": "center",
                    "padding": "7px 12px",
                    "border": "1px solid #334155",
                    "border-radius": "999px",
                    "background-color": "#1e293b",
                    "color": "#c7d2fe",
                    "font-size": "11px",
                    "font-weight": "700",
                    "letter-spacing": "0.12em"
                })
            ),

            Heading(
                "Build better web apps.",
                level=1,
                css=CSS({
                    "max-width": "760px",
                    "margin": "24px 0 16px",
                    "color": COLORS["hero_text"],
                    "font-size": "clamp(2.5rem, 6vw, 4.5rem)",
                    "font-weight": "800",
                    "line-height": "1.05",
                    "letter-spacing": "-0.055em"
                })
            ),

            Paragraph(
                "Reactive web applications, built with Python. "
                "Create interfaces, compose components, and build "
                "interactive experiences without making JavaScript "
                "the center of your workflow.",
                css=CSS({
                    "max-width": "680px",
                    "margin": "0",
                    "color": COLORS["hero_muted"],
                    "font-size": "clamp(1rem, 2vw, 1.2rem)",
                    "line-height": "1.8"
                })
            ),

            Div(
                [
                    Div(
                        "Python-first development",
                        css=CSS({
                            "color": "#e2e8f0",
                            "font-size": "13px",
                            "font-weight": "600"
                        })
                    ),
                    Div(
                        "Composable UI",
                        css=CSS({
                            "color": "#e2e8f0",
                            "font-size": "13px",
                            "font-weight": "600"
                        })
                    ),
                    Div(
                        "Built-in tooling",
                        css=CSS({
                            "color": "#e2e8f0",
                            "font-size": "13px",
                            "font-weight": "600"
                        })
                    ),
                ],
                css=CSS({
                    "display": "flex",
                    "flex-wrap": "wrap",
                    "gap": "12px 24px",
                    "margin-top": "30px"
                })
            )
        ],
        classes=["welcome-hero"],
        css=CSS({
            "padding": "clamp(32px, 7vw, 80px)",
            "border-radius": "24px",
            "background": (
                "radial-gradient(ellipse at top right, "
                "#312e81 0%, #0f172a 55%)"
            ),
            "box-shadow": "0 24px 60px rgba(15, 23, 42, 0.12)"
        })
    )

    feature_data = [
        {
            "label": "01 / INTERACTIVITY",
            "title": "Reactive UI",
            "description": (
                "Build dynamic interfaces with reusable Python "
                "components and a consistent rendering model."
            ),
            "accent": COLORS["primary"],
            "background": COLORS["primary_soft"]
        },
        {
            "label": "02 / DEVELOPMENT",
            "title": "Python-first",
            "description": (
                "Keep views, application logic, and validation "
                "close together in a familiar language."
            ),
            "accent": COLORS["success"],
            "background": "#ecfdf5"
        },
        {
            "label": "03 / PRODUCTIVITY",
            "title": "Built-in tools",
            "description": (
                "Bring forms, validation, authentication, and "
                "data access into one cohesive development workflow."
            ),
            "accent": COLORS["info"],
            "background": "#f0f9ff"
        },
    ]

    feature_cards = []

    for feature in feature_data:
        feature_cards.append(
            Card(
                [
                    Div(
                        feature["label"],
                        css=CSS({
                            "color": feature["accent"],
                            "font-size": "11px",
                            "font-weight": "800",
                            "letter-spacing": "0.1em"
                        })
                    ),
                    Heading(
                        feature["title"],
                        level=3,
                        css=CSS({
                            "margin": "18px 0 10px",
                            "color": COLORS["text"],
                            "font-size": "21px",
                            "font-weight": "750",
                            "letter-spacing": "-0.025em"
                        })
                    ),
                    Paragraph(
                        feature["description"],
                        css=CSS({
                            "margin": "0",
                            "color": COLORS["text_muted"],
                            "font-size": "14px",
                            "line-height": "1.8"
                        })
                    ),
                ],
                shadow=True,
                css=CSS({
                    "height": "100%",
                    "padding": "26px",
                    "border": f"1px solid {COLORS['border']}",
                    "border-radius": "18px",
                    "background-color": COLORS["surface"],
                    "box-shadow": "0 4px 18px rgba(15, 23, 42, 0.035)"
                })
            )
        )

    features = Section(
        [
            Div(
                "THE PLATFORM",
                css=CSS({
                    "margin-bottom": "10px",
                    "color": COLORS["primary"],
                    "font-size": "11px",
                    "font-weight": "800",
                    "letter-spacing": "0.14em"
                })
            ),
            Heading(
                "Everything you need to get started",
                level=2,
                css=CSS({
                    "margin": "0",
                    "color": COLORS["text"],
                    "font-size": "clamp(1.65rem, 3vw, 2.25rem)",
                    "font-weight": "800",
                    "line-height": "1.2",
                    "letter-spacing": "-0.04em"
                })
            ),
            Paragraph(
                "A focused foundation for building and shipping "
                "Python-powered web experiences.",
                css=CSS({
                    "max-width": "620px",
                    "margin": "14px 0 0",
                    "color": COLORS["text_muted"],
                    "font-size": "15px",
                    "line-height": "1.8"
                })
            ),
            Div(
                feature_cards,
                classes=["cards-grid"],
                css=CSS({
                    "display": "grid",
                    "grid-template-columns": (
                        "repeat(auto-fit, minmax(min(100%, 260px), 1fr))"
                    ),
                    "gap": "20px",
                    "margin-top": "30px",
                    "align-items": "stretch"
                })
            ),
        ],
        css=CSS({
            "padding": "clamp(28px, 5vw, 48px) 0"
        })
    )

    task_demo = Section(
        [
            Div(
                "SEE IT IN ACTION",
                css=CSS({
                    "margin-bottom": "10px",
                    "color": COLORS["primary"],
                    "font-size": "11px",
                    "font-weight": "800",
                    "letter-spacing": "0.14em"
                })
            ),
            Heading(
                "A practical reactive example",
                level=2,
                css=CSS({
                    "margin": "0",
                    "color": COLORS["text"],
                    "font-size": "clamp(1.65rem, 3vw, 2.25rem)",
                    "font-weight": "800",
                    "line-height": "1.2",
                    "letter-spacing": "-0.04em"
                })
            ),
            Paragraph(
                "Explore a task list powered by a user-defined Python "
                "component. It demonstrates how application logic and "
                "interface composition can work together.",
                css=CSS({
                    "max-width": "700px",
                    "margin": "14px 0 26px",
                    "color": COLORS["text_muted"],
                    "font-size": "15px",
                    "line-height": "1.8"
                })
            ),
            Div(
                [
                    TaskFilter(
                        tasks,
                        css=CSS({
                            "width": "100%",
                            "padding": "24px",
                            "background-color": COLORS["surface"],
                            "border": f"1px solid {COLORS['border']}",
                            "border-radius": "16px",
                            "box-sizing": "border-box"
                        })
                    )
                ],
                css=CSS({
                    "padding": "clamp(20px, 4vw, 32px)",
                    "border": f"1px solid {COLORS['border']}",
                    "border-radius": "20px",
                    "background-color": COLORS["surface"],
                    "box-shadow": "0 12px 35px rgba(15, 23, 42, 0.045)"
                })
            )
        ],
        css=CSS({
            "padding": "clamp(28px, 5vw, 48px)",
            "border": f"1px solid {COLORS['border']}",
            "border-radius": "24px",
            "background-color": COLORS["surface_muted"]
        })
    )

    return Main(
        [
            hero,
            features,
            task_demo,
            Div(
                [
                    Paragraph(
                        "Built with Templar.",
                        css=CSS({
                            "margin": "0",
                            "color": COLORS["text_muted"],
                            "font-size": "13px"
                        })
                    ),
                    Paragraph(
                        "Python in. Possibilities out.",
                        css=CSS({
                            "margin": "0",
                            "color": COLORS["text_muted"],
                            "font-size": "13px"
                        })
                    )
                ],
                css=CSS({
                    "display": "flex",
                    "flex-wrap": "wrap",
                    "justify-content": "space-between",
                    "gap": "12px",
                    "padding": "24px 0 8px"
                })
            )
        ],
        id="home-page",
        css=CSS({
            "width": "100%",
            "max-width": "1200px",
            "margin": "0 auto",
            "padding": "32px 24px 24px",
            "box-sizing": "border-box",
            "font-family": FONT,
            "color": COLORS["text"]
        })
    )