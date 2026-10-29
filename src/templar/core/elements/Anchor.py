import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Anchor(Element):
    """
    Anchor <a> element with scoped style and interactivity.
    Supports href, target, download, rel, and custom behaviors.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        href: Optional[str] = "#",
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        target: Optional[str] = None,
        download: Optional[str] = None,
        rel: Optional[str] = None,
        **props
    ) -> None:
        if href:
            props["href"] = href

        if target:
            props["target"] = target

        if download:
            props["download"] = download

        if rel:
            props["rel"] = rel

        # Initialize parent to None
        self.parent = None

        super().__init__("a", content, id=id, classes=classes, **props)

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

        """Ensure rel='noopener' when using target='_blank' for security."""
        # Parent-safe check not strictly needed here, but added for consistency

        if getattr(self, "parent", None) and self.props.get("target") == "_blank" and "rel" not in self.props:
            self.props["rel"] = "noopener noreferrer"

    def after_render(self, html_output: str) -> str:
        return super().after_render(html_output)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
