import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Tr(Element):
    """
    <tr> table row element.
    Typically contains <td> or <th> children.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("tr", content, id=id, classes=classes, **props)

    def default_styles(self, style: CSS):
        style.set("border-bottom", "1px solid #ccc")

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

        # Parent check: <tr> should be inside <thead>, <tbody>, or <tfoot>
        if not self.parent or self.parent.tag not in ["thead", "tbody", "tfoot"]:
            print(f"[Tr] Warning: <tr> should be inside <thead>, <tbody>, or <tfoot>, not <{self.parent.tag if self.parent else 'None'}>.")

        # Child check
        if self.content:
            for child in self.content:
                if not isinstance(child, Element) or child.tag not in ["td", "th"]:
                    print(f"[Tr] Warning: <tr> child must be <td> or <th>, found {child}")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    def update_dom(self):
        return self.script.render() if self.script else ""
