import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Aside(Element):
    """
    Aside <aside> element with scoped style and interactivity.
    Typically used for sidebars, notes, or callouts.
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

        super().__init__("aside", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """Default CSS for <aside> elements."""
        style.set("padding", "0.75rem") \
            .set("margin", "1rem 0") \
            .set("background-color", "#f9f9f9") \
            .set("border-left", "4px solid #ccc") \
            .set("font-size", "0.9rem") \
            .set("color", "#555")
        style.nested(" h4", {"margin-top": "0", "font-size": "1rem", "color": "#333"})
        style.nested(" p", {"margin-bottom": "0.5rem"})

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
        
        """Ensure semantic role is set for accessibility and parent-safe checks."""
        if getattr(self, "parent", None) and getattr(self.parent, "tag", None) != "body":
            print(f"[Aside] Warning: <aside> element is typically inside <body>")

        if "role" not in self.props:
            self.props["role"] = "complementary"
            print(f"[Aside] Added role='complementary' to id={self.props.get('id')}")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """Return JavaScript snippet for dynamic updates."""
        if self.script:
            return self.script.render()
        
        return ""
