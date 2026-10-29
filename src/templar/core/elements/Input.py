import sys
from typing import Optional, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Input(Element):
    """
    <input> element with scoped style, type/value support, and interactivity.
    Self-closing element; content is not used.
    """

    def __init__(
        self,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        type: str = "text",
        value: Optional[str] = None,
        placeholder: Optional[str] = None,
        parent: Optional[Element] = None,
        **props
    ):
        props["type"] = type

        if value is not None:
            props["value"] = value

        if placeholder is not None:
            props["placeholder"] = placeholder

        super().__init__("input", None, id=id, classes=classes, **props)

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
        
        """Ensure placeholder is defined and optionally acknowledge parent."""
        if "placeholder" not in self.props:
            self.props["placeholder"] = ""

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive DOM updates
    # -----------------------------
    def update_dom(self):
        """Return the JavaScript snippet for reactive patching."""
        if self.script:
            return self.script.render()
        
        return ""
