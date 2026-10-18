import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Td(Element):
    """
    <td> table cell element with default styling and optional JS hooks.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        colspan: Optional[int] = None,
        rowspan: Optional[int] = None,
        **props
    ):
        # Map HTML attributes
        if colspan:
            props["colspan"] = str(colspan)

        if rowspan:
            props["rowspan"] = str(rowspan)

        super().__init__("td", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("border", "1px solid #ccc") \
            .set("padding", "0.5rem") \
            .set("text-align", "left") \
            .set("vertical-align", "top")

    def default_scripts(self, script: Javascript):
        """
        Optional JS events can be added here for table cells.
        """
        element_id = self.props.get("id")

        if element_id:
            script.on(f"#{element_id}", "click", f"console.log('Td clicked: {element_id}');")

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
        Modify attributes or content before render if necessary.
        Performs parent check: ensures <td> is inside <tr>.
        """
        if self.parent and self.parent.tag != "tr":
            print(f"[Td] Warning: <td> element should be inside <tr>, not <{self.parent.tag}>.")

    def after_render(self, html_output: str) -> str:
        """
        Append scoped style/script blocks after the <td> HTML output.
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
        if self.script:
            return self.script.render()

        return ""
