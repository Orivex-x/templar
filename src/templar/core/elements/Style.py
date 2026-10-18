import sys

from .Element import Element
from ..Css import CSS

sys.dont_write_bytecode = True

class Style(Element):
    """
    <style> element for CSS rules.
    Holds raw CSS content and can integrate with the framework's CSS class.
    """
    def __init__(self, content: str = "", id: str = None, **attributes):
        # Ensure content is always a string
        super().__init__("style", content or "", id=id, **attributes)
        self.style = CSS()  # Optional: allow building CSS via framework

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
        Called before the <style> element is rendered.
        Can inject CSS rules from self.style if needed.
        Also checks for valid parent elements.
        """
        # Parent check: <style> should only be in <head> or top-level
        if self.parent and self.parent.tag not in ["head", None]:
            print(f"[Style] Warning: <style> element used inside <{self.parent.tag}>")

        if self.style and self.style.rules:
            # Combine raw content with framework CSS rules
            self.content = f"{self.content}\n{self.style.render()}"

    def after_render(self, html_output: str) -> str:
        """
        Returns the HTML output; <style> is self-contained.
        """
        return html_output

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        """
        Style elements typically don’t need DOM updates dynamically.
        """
        return ""
