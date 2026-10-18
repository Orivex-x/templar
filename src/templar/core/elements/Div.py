import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Div(Element):
    """
    <div> container element with scoped style and interactivity.
    Generic block-level container.
    """

    def __init__(
        self,
        content: Union[List[Element], Element, str] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        if content is not None and not isinstance(content, list):
            content = [content]

        # Initialize parent to None
        self.parent = None

        super().__init__("div", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("padding", "10px") \
            .set("background-color", "#f0f0f0") \
            .set("border-radius", "4px") \
            .set("box-sizing", "border-box")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")
        
        if element_id:
            # Dynamically style, or log clicks
            script.on(f"#{element_id}", "click", f"console.log('[Div] clicked: {element_id}');")

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

        if "role" not in self.props:
            self.props["role"] = "region"

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
    def update_dom(self) -> str:
        if self.script:
            return self.script.render()

        return ""
