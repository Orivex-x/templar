import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Nav(Element):
    """
    <nav> element with scoped style and interactivity.
    Typically, contains primary site navigation.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        parent: Optional[Element] = None,
        **props
    ):
        # Ensure content is always a list if provided
        if content is not None and not isinstance(content, list):
            content = [content]
        super().__init__("nav", content, id=id, classes=classes, **props)

        self.parent: Optional[Element] = parent

    def default_scripts(self, script: Javascript):
        pass

    # -----------------------------
    # Lifecycle
    # -----------------------------
    def on_init(self):
        pass

    def on_update(self, **new_props):
        super().on_update(**new_props)
        pass

    def on_destroy(self):
        pass
    
    # -----------------------------
    # Rendering hooks
    # -----------------------------
    def before_render(self):
        super().before_render()  # call generic logging
        
        # Optional: warn if parent is not <header> or <aside> or other container
        if self.parent and getattr(self.parent, "tag", None) not in ["header", "aside", "nav", "div", "section"]:
            print(f"[Nav] Warning: <nav> typically appears inside <header>, <aside>, <div>, or <section>")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive DOM updates
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
