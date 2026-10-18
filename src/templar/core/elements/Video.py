import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Video(Element):
    """
    <video> media element.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("video", content, id=id, classes=classes, **props)

    def default_styles(self, style: CSS):
        style.set("max-width", "100%").set("height", "auto")

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

        pass

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
