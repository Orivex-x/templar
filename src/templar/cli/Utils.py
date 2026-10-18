import sys, re, io
from bs4 import BeautifulSoup
from rich.panel import Panel
from rich.syntax import Syntax
from rich.console import Console
from rich.text import Text

sys.dont_write_bytecode = True

try:
    from lxml import html as lxml_html
    from lxml import etree as lxml_etree
    HAVE_LXML = True
except Exception:
    HAVE_LXML = False

def print_rich_help(parser, console: Console):
    """Render parser help output inside a styled Rich panel with syntax highlighting."""
    help_io = io.StringIO()
    parser.print_help(file=help_io)

    syntax = Syntax(help_io.getvalue(), "bash", theme="monokai", line_numbers=False)

    console.print(
        Panel(
            syntax,
            title="[bold cyan]Templar CLI[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

def print_rich_error(msg: str, console: Console):
    """Render errors in a styled Rich panel, consistent with CLI theme."""
    console.print(
        Panel(
            Text.assemble(
                ("[ERROR] ", "bold red"),
                (msg, "red"),
            ),
            title="[bold red]Templar Error[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )

def prettify_html(raw_html: str) -> str:
    """Prettify HTML using lxml if available, otherwise BeautifulSoup as a fallback."""
    doctype = ""
    match = re.match(r"(?is)^\s*(<!DOCTYPE[^>]*>)", raw_html)

    if match:
        doctype = match.group(1)

    if HAVE_LXML:
        try:
            parser = lxml_html.HTMLParser(remove_blank_text=True)
            tree = lxml_html.fromstring(raw_html, parser=parser)
            pretty = lxml_etree.tostring(
                tree, method="html", encoding="unicode", pretty_print=True
            ).strip()

            if doctype and not re.match(r"(?is)^\s*<!doctype", pretty):
                pretty = f"{doctype}\n{pretty}"

            return pretty
        except Exception:
            pass

    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        pretty = soup.prettify().strip()

        if doctype and not re.match(r"(?is)^\s*<!doctype", pretty):
            pretty = f"{doctype}\n{pretty}"

        return pretty
    except Exception:
        return raw_html
