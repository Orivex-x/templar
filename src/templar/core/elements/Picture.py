import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Picture(Element):
    """
    <picture> element for responsive images with multiple sources,
    supporting scoped styles and optional interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("picture", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("display", "block")\
            .set("max-width", "100%")\
            .set("margin", "0 auto")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            # Log clicks on the picture element
            script.on(f"#{element_id}", "click", f"console.log('Picture clicked: {element_id}');")

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

        # Optional parent check
        if self.parent and self.parent.tag not in ["figure", "div", "section", "article"]:
            print(f"[Picture] Warning: <picture> is usually nested inside <figure>, <div>, <section>, or <article> (parent id={self.parent.props.get('id')})")

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
    # Reactive DOM patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
