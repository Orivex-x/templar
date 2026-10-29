import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Tbody(Element):
    """
    <tbody> container for table rows.
    """
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ):
        super().__init__("tbody", content, id=id, classes=classes, **props)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """
        Optional default styles for tbody. Typically, left empty for flexibility.
        """
        pass

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
        Hook to adjust content or attributes before rendering.
        Performs parent check: ensures <tbody> is inside a <table>.
        """
        if self.parent and self.parent.tag != "table":
            print(f"[Tbody] Warning: <tbody> element should be inside <table>, not <{self.parent.tag}>.")

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """
        Returns JS snippet to update tbody dynamically.
        """
        if self.script:
            return self.script.render()

        return ""

