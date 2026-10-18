import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Svg(Element):
    """
    <svg> container element for scalable vector graphics.
    Supports content (like <circle>, <rect>, <path>), 
    scoped CSS, and JS for interactivity.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        width: Optional[str] = None,
        height: Optional[str] = None,
        viewBox: Optional[str] = None,
        **props
    ):
        if width:
            props["width"] = width

        if height:
            props["height"] = height

        if viewBox:
            props["viewBox"] = viewBox

        super().__init__("svg", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """
        Default styling for SVG: inline display and vertical alignment.
        """
        style.set("display", "inline-block").set("vertical-align", "middle")

    def default_scripts(self, script: Javascript):
        """
        Add JS behaviours to the SVG, e.g. animations or interactions.
        """
        element_id = self.props.get("id")
        if element_id:
            script.on(f"#{element_id}", "click", f"console.log('SVG {element_id} clicked');")

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
        Prepare SVG attributes or content before rendering.
        Performs parent check: warns if placed in disallowed parents.
        """
        if self.parent and self.parent.tag not in ["div", "span", "section", "body"]:
            print(f"[Svg] Warning: <svg> element inside <{self.parent.tag}> may be invalid HTML.")

    def after_render(self, html_output: str) -> str:
        """
        Append scoped style/script blocks after SVG HTML output.
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
        Return JS snippet for dynamically updating the SVG DOM.
        """
        return self.script.render() if self.script else ""
