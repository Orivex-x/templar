import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Title(Element):
    """
    <title> document title element.
    Should only exist inside <head>.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("title", content, id=id, classes=classes, **props)

    def default_styles(self, style: CSS):
        pass

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

        # Parent check: <title> should be inside <head>
        if not self.parent or self.parent.tag != "head":
            print(f"[Title] Warning: <title> should be inside <head>, not <{self.parent.tag if self.parent else 'None'}>.")

        if not self.content:
            print("[Title] Warning: <title> is empty.")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    def update_dom(self):
        return self.script.render() if self.script else ""
