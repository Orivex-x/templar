import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Q(Element):
    """
    <q> element for inline quotations with scoped styling and optional interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("q", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        # Add quotation marks via CSS and default color
        style.set("quotes", '"“" "”" "‘" "’"').set("color", "#444")
        style.nested("::before", {"content": "open-quote"})
        style.nested("::after", {"content": "close-quote"})

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
        
        # Parent check: <q> should typically be inside block-level elements like <p>, <blockquote>, <div>, <section>
        if self.parent and self.parent.tag not in ["p", "blockquote", "div", "section"]:
            print(f"[Q] Warning: <q> element is typically nested inside <p>, <blockquote>, <div>, or <section> (parent id={self.parent.props.get('id')})")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
