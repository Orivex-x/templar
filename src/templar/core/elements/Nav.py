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

        # Optional reference to parent element
        self.parent: Optional[Element] = parent

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        style.set("display", "block") \
            .set("background-color", "#f8f9fa") \
            .set("padding", "0.5rem 1rem")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            # Log hover events
            script.on(f"#{element_id}", "mouseenter", f"console.log('Nav hovered: {element_id}');")

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
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        final_output = html_output

        if style_block:
            final_output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            final_output += f"\n{script_block}"
            
        return final_output

    # -----------------------------
    # Reactive DOM updates
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""
