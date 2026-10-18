import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Audio(Element):
    """
    Audio <audio> element with scoped style and interactivity.
    Supports autoplay, controls, loop, and muted attributes.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        src: Optional[str] = None,
        autoplay: bool = False,
        controls: bool = True,
        loop: bool = False,
        muted: bool = False,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        if src:
            props["src"] = src

        if autoplay:
            props["autoplay"] = "autoplay"

        if controls:
            props["controls"] = "controls"

        if loop:
            props["loop"] = "loop"

        if muted:
            props["muted"] = "muted"

        if content is not None and not isinstance(content, list):
            content = [content]

        # Initialize parent to None
        self.parent = None

        super().__init__("audio", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("display", "block") \
            .set("margin", "1rem 0") \
            .set("max-width", "100%") \
            .set("outline", "none")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            selector = f"#{element_id}"

            script.on(selector, "play", f"console.log('[Audio] Playing: ' + this.src);")
            script.on(selector, "pause", f"console.log('[Audio] Paused: ' + this.src);")
            script.on(selector, "ended", f"console.log('[Audio] Ended: ' + this.src);")
            script.on(selector, "volumechange", f"console.log('[Audio] Volume changed: ' + this.volume);")
            script.on(selector, "error", f"console.error('[Audio] Error loading: ' + this.src);")

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
        
        # Parent-safe check (audio usually inside <body>)
        if getattr(self, "parent", None) and getattr(self.parent, "tag", None) != "body":
            print(f"[Audio] Warning: <audio> element is typically inside <body>")

        if "controls" not in self.props:
            self.props["controls"] = "controls"

    def after_render(self, html_output: str) -> str:
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        final_output = html_output

        if style_block:
            final_output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            final_output += f"\n{script_block}"

        return final_output

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
