import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Head(Element):
    """
    <head> element with scoped styles and scripts.
    Typically contains <title>, <meta>, <link>, and <script> elements.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        parent: Optional[Element] = None,
        **props
    ):
        if content is not None and not isinstance(content, list):
            content = [content]

        super().__init__("head", content, id=id, classes=classes, **props)

        self.parent: Optional[Element] = parent
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    def on_init(self):
        """Assign parent to children for ElementMatrix"""
        for child in getattr(self, "content", []):
            if isinstance(child, Element):
                child.parent = self

    def before_render(self):
        super().before_render()  # call generic logging

        self.on_init()

    def after_render(self, html_output: str) -> str:
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        final_output = html_output

        if style_block:
            final_output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            final_output += f"\n{script_block}"

        return final_output

    def update_dom(self):
        if self.script:
            return self.script.render()

        return ""