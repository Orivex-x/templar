import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Form(Element):
    """
    <form> element with scoped style and interactivity.
    Represents a container for form controls and handles submission.
    """

    def __init__(
        self,
        content: Union[List[Element], Element, str] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        parent: Optional[Element] = None,
        **props
    ):
        if content is not None and not isinstance(content, list):
            content = [content]

        super().__init__("form", content, id=id, classes=classes, **props)

        # Optional reference to parent element
        self.parent: Optional[Element] = parent

        # Optional style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("display", "flex") \
            .set("flex-direction", "column") \
            .set("gap", "0.5rem") \
            .set("margin", "1rem 0")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            # Prevent default submission and log
            script.on(f"#{element_id}", "submit", "event.preventDefault(); console.log('[Form] submitted');")

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

    def after_render(self, html_output: str) -> str:
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        final_output = html_output

        if style_block:
            final_output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            final_output += f"\n{script_block}"

        return final_output

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
