import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Figcaption(Element):
    """
    <figcaption> element with scoped style and optional interactivity.
    Typically used as a caption or description inside a <figure>.
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

        super().__init__("figcaption", content, id=id, classes=classes, **props)

        # Reference to parent element (optional)
        self.parent: Optional[Element] = parent

        # Optional style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("text-align", "center") \
            .set("font-size", "0.9rem") \
            .set("color", "#555") \
            .set("margin-top", "0.5rem") \
            .set("display", "block")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            script.on(f"#{element_id}", "click", f"console.log('[Figcaption] clicked: {element_id}');")

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
        
        # Parent check before rendering
        if not self.parent or self.parent.tag_name != "figure":
            print(f"[Figcaption] Warning: Figcaption id={self.props.get('id')} has no <figure> parent!")

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
