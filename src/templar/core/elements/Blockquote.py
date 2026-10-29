import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Blockquote(Element):
    """
    Blockquote <blockquote> element with scoped style and interactivity.
    Typically used for quoted sections of text.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        cite: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        if content is not None and not isinstance(content, list):
            content = [content]

        if cite:
            props["cite"] = cite

        # Initialize parent to None
        self.parent = None

        super().__init__("blockquote", content, id=id, classes=classes, **props)

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
    # Rendering hooks
    # -----------------------------
    def before_render(self):
        super().before_render()  # call generic logging
        
        # Parent-safe check (blockquote usually inside <body>)
        if getattr(self, "parent", None) and getattr(self.parent, "tag", None) not in [None, "body"]:
            print(f"[Blockquote] Warning: <blockquote> element is typically inside <body>")

        # Ensure role for accessibility
        if "role" not in self.props:
            self.props["role"] = "note"

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
