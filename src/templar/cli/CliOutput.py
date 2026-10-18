import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.console import Group
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich.pretty import Pretty

sys.dont_write_bytecode = True

class CliOutput:
    """
    Centralized CLI output handler for Templar.
    Provides consistent styling for:
    - Info messages
    - Errors
    - Panels
    - Tables
    - Syntax-highlighted code
    - Rich banners
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    # -------------------
    # Panel-based messages
    # -------------------
    def error(self, msg: str, title: str = "Error"):
        """Print a styled error panel in red."""
        self.console.print(
            Panel(
                Text(msg, style="bold red"),
                title=f"[bold red]{title}[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )

    def info(self, msg: str, title: str = "Info"):
        """Print a styled info panel in cyan."""
        self.console.print(
            Panel(
                Text(msg, style="green"),
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def success(self, msg: str, title: str = "Success"):
        """Print a styled success panel in green."""
        self.console.print(
            Panel(
                Text(msg, style="bold green"),
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def warning(self, msg: str, title: str = "Warning"):
        """Print a styled warning panel in yellow."""
        self.console.print(
            Panel(
                Text(msg, style="bold yellow"),
                title=f"[bold yellow]{title}[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )

    # -------------------
    # Banners
    # -------------------
    def banner(self, title: str, content: str = "", subtitle: Optional[str] = None):
        """Print a custom banner panel."""
        text = Text(content, style="cyan")
        panel_title = f"[bold cyan]{title}[/bold cyan]"

        if subtitle:
            panel_title += f" - [bold green]{subtitle}[/bold green]"
        
        self.console.print(Panel(text, title=panel_title, border_style="cyan", padding=(1, 2)))

    # -------------------
    # Panel
    # -------------------
    def panel(self, content, title: str = "", border_style: str = "cyan", padding=(1, 2)):
        """
        Generic panel printer. Accepts:
        - content: str, Text, Group, Columns, or other Rich renderable
        - content may also be a list/tuple of renderables
        """
        # Automatically wrap lists/tuples into a Rich Group
        if isinstance(content, (list, tuple)):
            content = Group(*content)

        # Convert plain strings to Text
        if isinstance(content, str):
            content = Text(content)

        self.console.print(
            Panel(
                content,
                title=f"[bold cyan]{title}[/bold cyan]" if title else "",
                border_style=border_style,
                padding=padding
            )
        )
    
    # -------------------
    # Tables
    # -------------------
    def table(
        self,
        columns: list,
        rows: list,
        title: str = "",
        column_styles: Optional[list] = None,
        border_style: str = "cyan",
        show_lines: bool = True,
    ):
        """
        Render a table.
        columns: list of column headers
        rows: list of row tuples/lists
        column_styles: optional list of styles per column
        """
        table = Table(title=title, border_style=border_style, show_lines=show_lines)

        for i, col in enumerate(columns):
            style = column_styles[i] if column_styles and i < len(column_styles) else "white"
            table.add_column(col, style=style, no_wrap=False)

        for row in rows:
            # Preserve Rich renderables (Text, Group, etc.)
            table.add_row(*[cell if isinstance(cell, (Text,)) else str(cell) for cell in row])

        self.console.print(table)

    # -------------------
    # Syntax Highlighting
    # -------------------
    def syntax(self, code: str, language: str = "python", theme: str = "monokai", line_numbers: bool = True):
        """Print syntax-highlighted code or template."""
        syntax = Syntax(code, language, theme=theme, line_numbers=line_numbers)
        self.console.print(Panel(syntax, title=f"[bold cyan]{language.upper()}[/bold cyan]", border_style="cyan"))

    # -------------------
    # Rich Pretty Printing
    # -------------------
    def pretty(self, obj):
        """Pretty-print Python objects with Rich coloring."""
        self.console.print(Pretty(obj, expand_all=True, indent_guides=True))

    # -------------------
    # HTML Preview
    # -------------------
    def html_preview(self, html: str, line_numbers: bool = True):
        """Render HTML code with syntax highlighting."""
        syntax = Syntax(html, "html", theme="monokai", line_numbers=line_numbers)
        self.console.print(Panel(syntax, title="[bold cyan]HTML Preview[/bold cyan]", border_style="cyan"))

    # -------------------
    # Generic text
    # -------------------
    def text(self, msg: str, style: str = "white"):
        """Print raw text with a style."""
        self.console.print(Text(msg, style=style))

    # -------------------
    # Success / Exit message
    # -------------------
    def exit(self, msg: str = "Exiting Templar shell"):
        """Print an exit panel."""
        self.console.print(
            Panel(
                Text(msg, style="bold cyan"),
                border_style="cyan",
                padding=(1, 2)
            )
        )
