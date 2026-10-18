import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Html(Element):
    """
    <html> element with scoped style and optional interactivity.
    Represents the root of the document.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        if content is not None and not isinstance(content, list):
            content = [content]

        super().__init__("html", content, id=id, classes=classes, **props)

        # Scoped placeholders for optional CSS/JS
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """Default styles for <html>."""
        style.set("height", "100%").set("width", "100%").set("box-sizing", "border-box")

    def default_scripts(self, script: Javascript):
        """Default JS for <html> root element."""
        # element_id = self.props.get("id")
        
        # if element_id:
        #     script.on(f"#{element_id}", "DOMContentLoaded", f"console.log('[Html] loaded: {element_id}');")

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
        
        """Prepare semantic attributes for <html>."""
        if "lang" not in self.props:
            self.props["lang"] = "en"
            
    def after_render(self, html_output: str) -> str:
        """Inject scoped style/script after <html> HTML if present."""
        return html_output

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """Return JS snippet for dynamic updates of <html>."""
        if self.script:
            return self.script.render()
        
        return ""
