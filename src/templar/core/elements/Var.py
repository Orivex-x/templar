import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Var(Element):
    """
    <var> element - represents variables in code or math.
    Supports optional id, classes, and scoped styles/scripts.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("var", content, id=id, classes=classes, **props)

    def default_styles(self, style: CSS):
        style.set("font-style", "italic").set("color", "#d6336c")

    def default_scripts(self, script: Javascript):
        pass

    def on_init(self):
        pass
    
    def on_update(self, **new_props):
        super().on_update(**new_props)
        pass

    def on_destroy(self):
        pass

    def before_render(self):
        super().before_render()  # call generic logging

        # Parent check: <var> should be inside inline contexts
        if self.parent and self.parent.tag not in ["p", "span", "code", "li", "body"]:
            print(f"[Var] Warning: <var> element may not be valid inside <{self.parent.tag}>.")

    def after_render(self, html_output: str) -> str:
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        output = html_output

        if style_block:
            output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            output += f"\n{script_block}"

        return output

    def update_dom(self):
        return self.script.render() if self.script else ""
