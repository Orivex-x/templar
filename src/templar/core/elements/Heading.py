import sys
from typing import List, Optional, Union

from .Element import Element

sys.dont_write_bytecode = True


class Heading(Element):
    """Semantic heading helper that renders h1 through h6."""

    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        level: int = 1,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        level = max(1, min(6, int(level)))
        super().__init__(f"h{level}", content, id=id, classes=classes, **props)
