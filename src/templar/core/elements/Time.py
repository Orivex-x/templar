import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Time(Element):
    """
    <time> element representing dates and/or times.
    Can include a `datetime` attribute to indicate the machine-readable value.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        datetime: Optional[str] = None,
        **props
    ):
        if datetime:
            props["datetime"] = datetime

        super().__init__("time", content, id=id, classes=classes, **props)

    def default_styles(self, style: CSS):
        style.set("font-style", "italic").set("color", "#555")

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

        if "datetime" in self.props:
            print(f"[Time] Rendering with datetime={self.props['datetime']}")

        # Parent check: <time> should be inside <p>, <li>, <div>, or inline context
        if self.parent and self.parent.tag not in ["p", "li", "div", "span", "body"]:
            print(f"[Time] Warning: <time> element may not be valid inside <{self.parent.tag}>.")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    def update_dom(self):
        return self.script.render() if self.script else ""
