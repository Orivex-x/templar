import sys
from typing import Optional

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Meta(Element):
    """
    <meta> element - self-closing with optional interactivity.
    """

    def __init__(self, id: str = None, parent: Optional[Element] = None, **props):
        super().__init__("meta", None, id=id, **props)

        # Optional reference to parent element
        self.parent: Optional[Element] = parent

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """Meta tag does not require styling."""
        pass

    def default_scripts(self, script: Javascript):
        pass

    # -----------------------------
    # Lifecycle
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

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive DOM updates
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
