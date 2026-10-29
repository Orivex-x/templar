import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Select(Element):
    """
    <select> element for dropdowns, optionally containing <option> or <optgroup> elements.
    Supports default styles, scripts, and lifecycle hooks.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        multiple: bool = False,
        disabled: bool = False,
        **props
    ):
        # Add standard select attributes
        if multiple:
            props["multiple"] = "multiple"

        if disabled:
            props["disabled"] = "disabled"

        super().__init__("select", content, id=id, classes=classes, **props)

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
        
        # Validate parent element
        if self.parent and self.parent.tag in ["p", "span", "a", "button"]:
            print(f"[Select] Warning: <select> should not be a child of <{self.parent.tag}>")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
