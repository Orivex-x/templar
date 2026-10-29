import sys
from typing import Optional, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Img(Element):
    """
    <img> element with scoped style and interactivity.
    Self-closing element; content is not used.
    """

    def __init__(
        self,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        src: Optional[str] = None,
        alt: Optional[str] = None,
        width: Optional[str] = None,
        height: Optional[str] = None,
        parent: Optional[Element] = None,
        **props
    ):
        if src:
            props["src"] = src

        if alt:
            props["alt"] = alt

        if width:
            props["width"] = width

        if height:
            props["height"] = height

        super().__init__("img", None, id=id, classes=classes, **props)

        self.parent: Optional[Element] = parent

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
        
        """Ensure 'alt' attribute is present and optionally acknowledge parent."""
        if "alt" not in self.props:
            self.props["alt"] = ""

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """Return the JavaScript snippet for reactive updates."""
        if self.script:
            return self.script.render()
        
        return ""
