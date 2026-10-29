import sys
from typing import Optional

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Link(Element):
    """
    <link> element for CSS/stylesheet inclusion or other external resources.
    Self-closing element. Primarily used in <head>.
    """

    def __init__(
        self,
        href: Optional[str] = None,
        rel: Optional[str] = "stylesheet",
        type: Optional[str] = "text/css",
        id: Optional[str] = None,
        classes: Optional[list[str]] = None,
        **props
    ):
        if href:
            props["href"] = href

        if rel:
            props["rel"] = rel

        if type:
            props["type"] = type

        super().__init__("link", None, id=id, classes=classes, **props)

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
        
        # Validate that <link> is inside <head> if parent exists
        if self.parent and getattr(self.parent, "tag", None) != "head":
            print(f"[Link] Warning: <link> element is typically used inside <head>")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive DOM updates
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
