import sys, html
sys.dont_write_bytecode = True

"""
Wraps user input to be escaped when rendering.
"""
class SafeString:
    def __init__(self, content):
        self.content = content

    """
    Escape HTML special characters.
    """
    def render(self):
        return html.escape(str(self.content)) 
