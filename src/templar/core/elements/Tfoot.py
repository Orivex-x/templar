import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Tfoot(Element):
    """
    <tfoot> table footer container element.
    Typically used inside <table> to group footer rows.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("tfoot", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("font-weight", "bold") \
            .set("background-color", "#f9f9f9")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            script.on(f"#{element_id}", "mouseenter", f"console.log('[Tfoot] Hover: {element_id}');")
            script.on(f"#{element_id}", "mouseleave", f"console.log('[Tfoot] Leave: {element_id}');")

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

        # Parent check: <tfoot> must be inside <table>
        if not self.parent or self.parent.tag != "table":
            print(f"[Tfoot] Warning: <tfoot> should be inside <table>, not <{self.parent.tag if self.parent else 'None'}>.")

    def after_render(self, html_output: str) -> str:
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        output = html_output

        if style_block:
            output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            output += f"\n{script_block}"

        return output

    def update_dom(self):
        return self.script.render() if self.script else ""
