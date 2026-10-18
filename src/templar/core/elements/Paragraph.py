import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Paragraph(Element):
    """
    <p> element for text content with scoped style and optional interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("p", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("margin", "0.5rem 0").set("line-height", "1.5").set("color", "#333")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")
        
        if element_id:
            # Log clicks on the paragraph
            script.on(f"#{element_id}", "click", f"console.log('Paragraph clicked: {element_id}');")

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

        # Parent-specific check
        if self.parent and self.parent.tag in ["p", "span", "label"]:
            print(f"[Paragraph] Warning: <p> should not be nested inside <{self.parent.tag}> (id={self.parent.props.get('id')})")

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
    def update_dom(self) -> str:
        if self.script:
            return self.script.render()
        
        return ""
