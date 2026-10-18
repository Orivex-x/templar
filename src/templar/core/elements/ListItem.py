import sys
from typing import Optional, Union, List

from .Element import Element
from ..Css import CSS
from ..Javascript import Javascript

sys.dont_write_bytecode = True

class ListItem(Element):
    """
    <li> element - represents an item in a list (<ul> or <ol>).
    Should only appear inside <ul>, <ol>, or <menu>.
    Supports scoped styles and optional interactivity.
    """

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        parent: Optional[Element] = None,
        **props
    ):
        super().__init__("li", content, id=id, classes=classes, **props)
        # Optional reference to parent element
        self.parent: Optional[Element] = parent

    # -----------------------------
    # Scoped defaults
    # -----------------------------
    def default_styles(self, style: CSS):
        # Default spacing for readability
        style.set("margin-bottom", "0.5rem").set("padding-left", "1rem")

    def default_scripts(self, script: Javascript):
        element_id = self.props.get("id")

        if element_id:
            # Optional: log clicks for debugging or reactive behavior
            script.on(f"#{element_id}", "click", f"console.log('ListItem clicked: {element_id}');")

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
        
        # Validate parent element
        if self.parent and self.parent.tag not in ["ul", "ol", "menu"]:
            print(f"[ListItem] Warning: <li> should be a child of <ul>, <ol>, or <menu>")

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
