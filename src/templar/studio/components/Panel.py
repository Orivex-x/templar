from templar.core.elements.Div import Div

def panel(content, *, classes=None):
    return Div(
        content,
        classes=["studio-panel", *(classes or [])]
    )