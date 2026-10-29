import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Body(Element):
    """
    Body <body> element with scoped style and interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        if content is not None and not isinstance(content, list):
            content = [content]

        # Initialize parent to None
        self.parent = None

        super().__init__("body", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """Default CSS for the <body> element."""
        style.set("margin", "0") \
            .set("padding", "0") \
            .set("font-family", "Arial, sans-serif") \
            .set("line-height", "1.5") \
            .set("background-color", "#ffffff") \
            .set("color", "#333")

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
        
        """Parent-safe check (body usually inside <html>) and accessibility role."""
        if getattr(self, "parent", None) and getattr(self.parent, "tag", None) not in [None, "html"]:
            print(f"[Body] Warning: <body> element is typically inside <html>")

        if "role" not in self.props:
            self.props["role"] = "document"

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """Return JS snippet for dynamic updates."""
        if self.script:
            print("[Body] update_dom called")

            return self.script.render()

        return ""
