import sys

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Script(Element):
    """
    <script> element: embeds or links JavaScript. Supports inline content or src attribute.
    Provides lifecycle hooks and reactive updates.
    """

    def __init__(
        self,
        content: str = "",
        src: str|None = None,
        id: str|None = None,
        classes: list|None = None,
        **attributes
    ):
        if src:
            attributes["src"] = src

        super().__init__("script", content, id=id, classes=classes, **attributes)

        # Scoped JS object for reactive patching
        self.script = Javascript()

        if content:
            self.script._add_snippet(content)

    def default_scripts(self, script: Javascript):
        # Already stores content as snippet
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

        # Parent check: <script> is ideally in <head> or just before </body>
        if self.parent and self.parent.tag not in ["head", "body"]:
            print(f"[Script] Warning: <script> element is typically nested in <head> or <body> (parent id={self.parent.props.get('id')})")

    def after_render(self, html_output: str) -> str:
        return html_output

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
