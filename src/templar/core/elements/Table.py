import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Table(Element):
    """
    <table> element representing an HTML table.
    Supports optional content (thead, tbody, tfoot, tr, etc.), 
    scoped CSS, and JS for interactivity.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("table", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("border-collapse", "collapse") \
            .set("width", "100%") \
            .set("margin-bottom", "1rem")

    def default_scripts(self, script: Javascript):
        pass

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
        Adjust content or attributes before rendering if needed.
        Performs parent check: warns if placed in disallowed parents.
        """
        if self.parent and self.parent.tag not in ["div", "section", "body"]:
            print(f"[Table] Warning: <table> element inside <{self.parent.tag}> may be invalid HTML.")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """
        Return JS snippet to dynamically update the table DOM.
        """
        return self.script.render() if self.script else ""
