import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class Canvas(Element):
    """
    Canvas <canvas> element for drawing graphics with JavaScript.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        width: Optional[int] = 300,
        height: Optional[int] = 150,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        if width:
            props["width"] = width

        if height:
            props["height"] = height

        if content is not None and not isinstance(content, list):
            content = [content]

        # Initialize parent to None
        self.parent = None

        super().__init__("canvas", content, id=id, classes=classes, **props)

        # Optional: style & script placeholders
        self.style: Optional[CSS] = self.style or CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = self.script or Javascript(f"#{id}") if id else None

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        """Default CSS for canvas element."""
        style.set("border", "1px solid #ccc") \
            .set("display", "block") \
            .set("margin", "1rem auto") \
            .set("background-color", "#fff")

    def default_scripts(self, script: Javascript):
        """Attach a sample JS drawing if id is set."""
        element_id = self.props.get("id")

        if element_id:
            script.on("document", "DOMContentLoaded", f"""
                var canvas = document.getElementById('{element_id}');
                if (canvas) {{
                    var ctx = canvas.getContext('2d');
                    ctx.fillStyle = '#007BFF';
                    ctx.fillRect(10, 10, 100, 50);
                    console.log('[Canvas] Initialized drawing for #{element_id}');
                }}
            """)

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
        
        # Parent-safe check
        if getattr(self, "parent", None):
            print(f"[Canvas] Rendering inside parent tag: {getattr(self.parent, 'tag', None)}")

        # Ensure accessibility role
        if "role" not in self.props:
            self.props["role"] = "img"

    def after_render(self, html_output: str) -> str:
        """Inject style/script after canvas HTML if present."""
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        result = html_output

        if style_block:
            result += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            result += f"\n{script_block}"

        return result

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
