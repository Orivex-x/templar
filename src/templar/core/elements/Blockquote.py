import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Blockquote(Element):
    """
    Blockquote <blockquote> element with scoped style and interactivity.
    Typically used for quoted sections of text.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        cite: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        if content is not None and not isinstance(content, list):
            content = [content]

        if cite:
            props["cite"] = cite

        # Initialize parent to None
        self.parent = None

        super().__init__("blockquote", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("margin", "1rem 0") \
             .set("padding", "0.5rem 1rem") \
             .set("border-left", "4px solid #ccc") \
             .set("color", "#555") \
             .set("font-style", "italic") \
             .set("background-color", "#fdfdfd")

        # Nested styles for <cite>
        style.nested(" cite", {
            "display": "block",
            "font-size": "0.85rem",
            "margin-top": "0.5rem",
            "color": "#777",
            "text-align": "right"
        })

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")
        if element_id:
            script.on(f"#{element_id}", "click", f"console.log('[Blockquote] Clicked: {element_id}');")
            script.on(f"#{element_id}", "mouseenter", "this.style.borderLeftColor = '#007BFF';")
            script.on(f"#{element_id}", "mouseleave", "this.style.borderLeftColor = '#ccc';")

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
        
        # Parent-safe check (blockquote usually inside <body>)
        if getattr(self, "parent", None) and getattr(self.parent, "tag", None) not in [None, "body"]:
            print(f"[Blockquote] Warning: <blockquote> element is typically inside <body>")

        # Ensure role for accessibility
        if "role" not in self.props:
            self.props["role"] = "note"

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
