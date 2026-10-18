import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Code(Element):
    """
    Code <code> element for inline or block code snippets.
    Supports optional language metadata and scoped styling/scripts.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        language: Optional[str] = None,
        **props
    ) -> None:
        if language:
            props["data-lang"] = language

        # Initialize parent to None
        self.parent = None

        super().__init__("code", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("font-family", "monospace") \
            .set("background-color", "#f5f5f5") \
            .set("padding", "0.2rem 0.4rem") \
            .set("border-radius", "4px") \
            .set("font-size", "0.95rem") \
            .set("color", "#c7254e")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            # Log on DOMContentLoaded
            script.on("document", "DOMContentLoaded", f"""
                var el = document.getElementById('{element_id}');
                if (el) {{
                    console.log('[Code] Loaded code snippet id={element_id}');
                }}
            """)

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
            print(f"[Code] Rendering inside parent tag: {getattr(self.parent, 'tag', None)}")

        if "role" not in self.props:
            self.props["role"] = "code"
            
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
