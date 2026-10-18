import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Section(Element):
    """
    <section> element: semantic container for related content.
    Supports optional content, default styles, and interactive JS.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        # Ensure content is a list if provided
        if content is not None and not isinstance(content, list):
            content = [content]

        super().__init__("section", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        # Basic spacing and readability
        style.set("padding", "1rem").set("margin", "1rem 0")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            # Example click listener for the section
            script.on(f"#{element_id}", "click", f"console.log('Section clicked: {element_id}');")

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

        # Validate parent element
        if self.parent and self.parent.tag in ["p", "span", "a", "button"]:
            print(f"[Section] Warning: <section> should not be a child of <{self.parent.tag}>")

    def after_render(self, html_output: str) -> str:
        # Append scoped styles and scripts after rendering
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        output = html_output

        if style_block:
            output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            output += f"\n{script_block}"

        return output

    # -----------------------------
    # Reactive DOM updates
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
