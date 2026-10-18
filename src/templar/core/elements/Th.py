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

    def default_styles(self, style: CSS):
        style.set("border", "1px solid #ccc") \
            .set("padding", "0.5rem") \
            .set("text-align", "left") \
            .set("background-color", "#f2f2f2") \
            .set("font-weight", "bold")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            script.on(f"#{element_id}", "click", f"console.log('[Th] Clicked: {element_id}');")

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
