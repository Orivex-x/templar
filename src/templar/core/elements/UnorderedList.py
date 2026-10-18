import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class UnorderedList(Element):
    """
    <ul> unordered list element.
    Represents a semantic list container with optional id, classes, and scoped styling.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("ul", content, id=id, classes=classes, **props)

    def default_styles(self, style: CSS):
        style.set("list-style-type", "disc").set("padding-left", "1.5rem")

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

        # Parent check: <ul> should be inside <body>, <div>, <section>, <article>, or <li>
        if self.parent and self.parent.tag not in ["body", "div", "section", "article", "li"]:
            print(f"[UnorderedList] Warning: <ul> may not be valid inside <{self.parent.tag}>.")

        # Child check: <ul> children should be <li>
        if self.content:
            for child in self.content:
                if not isinstance(child, Element) or child.tag != "li":
                    print(f"[UnorderedList] Warning: <ul> child must be <li>, found {child}")

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
