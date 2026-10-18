import sys

from .Element import Element

sys.dont_write_bytecode = True

class Wbr(Element):
    """
    <wbr> - word break opportunity. Self-closing element.
    """
    def __init__(self, **props):
        # No content, no default styles/scripts
        super().__init__("wbr", None, **props)
