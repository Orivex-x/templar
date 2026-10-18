import sys

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Source(Element):
    """
    <source> element (self-closing) for <audio> or <video> sources.
    Typically includes attributes like src, type, and media.
    """
    def __init__(
        self,
        src: str = None,
        type_: str = None,
        media: str = None,
        **attributes
    ):
        # Set standard source attributes if provided
        if src:
            attributes["src"] = src

        if type_:
            attributes["type"] = type_

        if media:
            attributes["media"] = media

        super().__init__("source", None, **attributes)

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        # Self-closing element; typically no styles required
        pass

    def default_scripts(self, script: Javascript):
        # No scripts needed for <source>
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
        
        # Validate parent element
        if self.parent and self.parent.tag not in ["audio", "video"]:
            print(f"[Source] Warning: <source> should only be a child of <audio> or <video>")

    def after_render(self, html_output: str) -> str:
        return html_output

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        return ""
