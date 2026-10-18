import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Dd(Element):
    """
    Description element <dd> within a <dl> list.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        if content is not None and not isinstance(content, list):
            content = [content]

        # Initialize parent to None
        self.parent = None

        super().__init__("dd", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("margin-left", "1.5rem") \
            .set("color", "#333") \
            .set("padding", "0.25rem 0") \
            .set("font-size", "0.95rem")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            # Log when the element is hovered
            script.on(f"#{element_id}", "mouseenter", f"console.log('[Dd] Hovered {element_id}');")

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
        
        # Parent-safe check
        if getattr(self, "parent", None):
            print(f"[Dd] Rendering inside parent tag: {getattr(self.parent, 'tag', None)}")

        if "role" not in self.props:
            self.props["role"] = "definition"

    def after_render(self, html_output: str) -> str:
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        result = html_output

        if style_block:
            result += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            result += f"\n{script_block}"

        return result

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
