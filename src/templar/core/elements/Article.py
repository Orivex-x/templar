import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Article(Element):
    """
    Article <article> element with scoped style and interactivity.
    Typically used for self-contained content sections.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        # Normalize single element into a list
        if content is not None and not isinstance(content, list):
            content = [content]

        # Initialize parent to None
        self.parent = None

        super().__init__("article", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """Default CSS for articles."""
        style.set("padding", "1rem") \
            .set("margin", "1rem 0") \
            .set("line-height", "1.6") \
            .set("background-color", "#fff") \
            .set("border-radius", "6px") \
            .set("box-shadow", "0 1px 3px rgba(0,0,0,0.1)")

        # Nested rules for headings and paragraphs
        style.nested(" h1", {"font-size": "1.5rem", "margin-bottom": "0.5rem"})
        style.nested(" h2", {"font-size": "1.25rem", "margin-bottom": "0.5rem"})
        style.nested(" p", {"margin-bottom": "1rem"})

    def default_scripts(self, script: Javascript):
        pass

    # -----------------------------
    # Lifecycle hooks
    # -----------------------------
    def on_init(self):
        pass

    def on_update(self, **new_props):
        super().on_update(**new_props)
        pass

    def on_destroy(self):
        pass

    # -----------------------------
    # Rendering hooks
    # -----------------------------
    def before_render(self):
        super().before_render()  # call generic logging
        
        """Prepare props before rendering and perform parent checks."""
        # Parent-safe check (optional for semantic warnings)
        if getattr(self, "parent", None) and getattr(self.parent, "tag", None) != "head":
            print(f"[Article] Warning: <article> element is typically not inside <head>")

        # Ensure ARIA role
        if "role" not in self.props:
            self.props["role"] = "article"

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """Return the JavaScript snippet for dynamic updates."""
        if self.script:
            return self.script.render()
        
        return ""
