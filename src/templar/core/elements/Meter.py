import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Meter(Element):
    """
    <meter> element with scoped style and interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        parent: Optional[Element] = None,
        **props
    ):
        super().__init__("meter", content, id=id, classes=classes, **props)

        # Optional reference to parent element
        self.parent: Optional[Element] = parent

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("width", "100%") \
            .set("height", "1.5rem") \
            .set("background-color", "#e0e0e0") \
            .set("border-radius", "4px")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")
        if element_id:
            # Log current value when clicked
            script.on(f"#{element_id}", "click", "console.log('Meter clicked: ' + this.value);")

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

        # Warn if parent is not a <form> or block-level container
        if self.parent and getattr(self.parent, "tag", None) not in ["form", "div", "section", "main"]:
            print(f"[Meter] Warning: <meter> typically appears inside <form>, <div>, <section>, or <main>")

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
    # Reactive DOM updates
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()

        return ""
