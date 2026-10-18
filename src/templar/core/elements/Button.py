import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Button(Element):
    """
    Button <button> element with scoped style and interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        type: Optional[str] = "button",
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        disabled: bool = False,
        **props
    ) -> None:
        if type:
            props["type"] = type

        if disabled:
            props["disabled"] = "disabled"

        if content is not None and not isinstance(content, list):
            content = [content]

        # Initialize parent to None
        self.parent = None

        super().__init__("button", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """Default CSS for buttons."""
        style.set("padding", "0.5rem 1rem") \
            .set("border", "1px solid #007BFF") \
            .set("background-color", "#007BFF") \
            .set("color", "#fff") \
            .set("border-radius", "4px") \
            .set("cursor", "pointer") \
            .set("font-size", "1rem") \
            .set("transition", "background-color 0.2s ease")

        # Nested pseudo-classes
        style.nested(":hover", {"background-color": "#0056b3"})
        style.nested(":disabled", {"background-color": "#cccccc", "cursor": "not-allowed"})

    def default_scripts(self, script: Javascript):
        """Default JS for button interactions."""
        element_id = self.props.get("id")

        if element_id:
            selector = f"#{element_id}"
            script.on(selector, "click", f"console.log('[Button] Clicked id={element_id}');")

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
        
        """Parent-safe check and ensure button has type attribute."""
        if "type" not in self.props:
            self.props["type"] = "button"

    def after_render(self, html_output: str) -> str:
        """Inject scoped <style> and <script> after HTML if present."""
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
        """Return JS snippet for dynamic updates."""
        if self.script:
            return self.script.render()
        
        return ""
