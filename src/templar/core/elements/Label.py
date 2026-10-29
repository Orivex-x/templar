import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Label(Element):
    """
    <label> element for form inputs with scoped style and interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        parent: Optional[Element] = None,
        **props
    ):
        super().__init__("label", content, id=id, classes=classes, **props)

        # Optional reference to parent element
        self.parent: Optional[Element] = parent

        # Scoped placeholders for optional CSS/JS
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("font-weight", "bold") \
            .set("margin-bottom", "0.25rem") \
            .set("display", "inline-block") \
            .set("cursor", "pointer")

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
        
        """
        Ensure 'for' attribute correctly associates with an input element.
        Optionally acknowledge parent element if set.
        """
        if "for" not in self.props and self.props.get("id"):
            self.props["for"] = self.props["id"]

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive DOM updates
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
