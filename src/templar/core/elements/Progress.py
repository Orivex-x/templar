import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Progress(Element):
    """
    <progress> element for displaying progress bars with optional styles and interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        value: Optional[float] = None,
        max: Optional[float] = 100,
        **props
    ):
        # Set the value and max attributes if provided
        if value is not None:
            props["value"] = value

        if max is not None:
            props["max"] = max

        super().__init__("progress", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("width", "100%")\
            .set("height", "1.25rem")\
            .set("appearance", "none")\
            .set("background-color", "#e0e0e0")
        style.nested("::-webkit-progress-bar", {"background-color": "#e0e0e0"})
        style.nested("::-webkit-progress-value", {"background-color": "#007bff"})
        style.nested("::-moz-progress-bar", {"background-color": "#007bff"})

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            # Log changes for reactive behaviour
            script.on(f"#{element_id}", "change", f"console.log('Progress updated: {element_id}');")

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

        # Optional parent check for semantic correctness
        if self.parent and self.parent.tag not in ["div", "section", "article", "figure"]:
            print(f"[Progress] Warning: <progress> is typically nested inside <div>, <section>, <article>, or <figure> (parent id={self.parent.props.get('id')})")

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
