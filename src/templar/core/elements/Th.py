import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Th(Element):
    """
    <th> table header cell element.
    Typically used inside <thead> or <tr>.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        scope: Optional[str] = None,  # "col" or "row"
        **props
    ):
        if scope:
            props["scope"] = scope

        super().__init__("th", content, id=id, classes=classes, **props)

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

        # Parent check: <th> must be inside <thead> or <tr>
        if not self.parent or self.parent.tag not in ["thead", "tr"]:
            print(f"[Th] Warning: <th> should be inside <thead> or <tr>, not <{self.parent.tag if self.parent else 'None'}>.")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    def update_dom(self):
        return self.script.render() if self.script else ""
