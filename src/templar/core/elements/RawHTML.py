import sys
sys.dont_write_bytecode = True

class RawHTML:
    """
    Wraps raw HTML strings that should not be escaped.
    Can be used as content inside Element children.
    """

    def __init__(self, content: str):
        self.content = content

    # -----------------------------
    # Lifecycle hooks (optional)
    # -----------------------------
    def on_init(self):
        pass

    def on_update(self, new_content: str):
        self.content = new_content
        pass

    def on_destroy(self):
        pass

    # -----------------------------
    # Render method
    # -----------------------------
    def render(self) -> str:
        return self.content
