import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Summary(Element):
    """
    <summary> element - used within <details> for summary content.
    Supports content, optional scripts, styles, and lifecycle hooks.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("summary", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """
        Default styling for <summary>: cursor pointer and bold text.
        """
        style.set("cursor", "pointer").set("font-weight", "bold")

    def default_scripts(self, script: Javascript):
        """
        Optional JS to handle summary click events.
        """
        element_id = self.props.get("id")

        if element_id:
            script.on(
                f"#{element_id}",
                "click",
                f"console.log('Summary clicked: {element_id}');"
            )

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
        Called before the <summary> is rendered.
        Checks that parent element is <details>.
        """
        if self.parent and self.parent.tag != "details":
            print(f"[Summary] Warning: <summary> element should only be inside <details>, not <{self.parent.tag}>")

    def after_render(self, html_output: str) -> str:
        """
        Appends scoped style/script blocks after the HTML output.
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
        """
        Returns JS snippet to update the <summary> dynamically.
        """
        if self.script:
            return self.script.render()
        
        return ""
