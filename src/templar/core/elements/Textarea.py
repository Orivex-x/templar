import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Textarea(Element):
    """
    <textarea> HTML element with default styling and optional JS interactivity.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        placeholder: Optional[str] = None,
        readonly: bool = False,
        disabled: bool = False,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        **props
    ):
        # Map HTML attributes
        if placeholder:
            props["placeholder"] = placeholder

        if readonly:
            props["readonly"] = "readonly"

        if disabled:
            props["disabled"] = "disabled"

        if rows:
            props["rows"] = str(rows)

        if cols:
            props["cols"] = str(cols)

        super().__init__("textarea", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """
        Default styling for textarea.
        """
        style.set("width", "100%") \
            .set("min-height", "100px") \
            .set("padding", "0.5rem") \
            .set("border", "1px solid #ccc") \
            .set("border-radius", "4px") \
            .set("resize", "vertical")

    def default_scripts(self, script: Javascript):
        """
        Optional JS to track input events.
        """
        element_id = self.props.get("id")

        if element_id:
            script.on(f"#{element_id}", "input", f"console.log('Textarea input: {element_id}');")

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

        """
        Modify or inject attributes/content before render.
        Performs parent check: should be inside form-related container.
        """
        allowed_parents = {"form", "div", "fieldset"}
        
        if self.parent and self.parent.tag not in allowed_parents:
            print(f"[Textarea] Warning: <textarea> element should be inside one of {allowed_parents}, not <{self.parent.tag}>.")

    def after_render(self, html_output: str) -> str:
        """
        Append scoped style/script blocks after the <textarea> HTML output.
        """
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        output = html_output

        if style_block:
            output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            output += f"\n{script_block}"

        return output

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """
        Returns JavaScript snippet for dynamic updates to the textarea.
        """
        return self.script.render() if self.script else ""
