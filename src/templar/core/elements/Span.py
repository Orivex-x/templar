import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Span(Element):
    """
    <span> inline HTML element.
    Can hold content, inline text, or child elements, and supports optional CSS and JS hooks.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("span", content, id=id, classes=classes, **props)

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
    # Render hooks
    # -----------------------------
    def before_render(self):
        super().before_render()  # call generic logging

        """
        Executed before rendering the <span> element.
        Warn if used inside disallowed parent elements.
        """
        disallowed_parents = ["p"]  # E.g.: prevent <span> as direct child of <p>

        if self.parent and self.parent.tag in disallowed_parents:
            print(f"[Span] Warning: <span> used inside <{self.parent.tag}>")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """
        Return the JavaScript snippet to update the span element dynamically if needed.
        """
        if self.script:
            return self.script.render()
        
        return ""
