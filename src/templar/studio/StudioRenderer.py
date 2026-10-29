from pathlib import Path

from templar.Renderer import Renderer
from templar.core.elements import Html, Head, Body, Meta, Title, Style
from templar.core.elements.ElementMatrix import ElementMatrix
from templar.studio.app import build_studio_page

class StudioRenderer(Renderer):
    """Render Studio pages using Templar's native element tree."""

    STUDIO_PREFIX = "__templar_studio_"
    TEMPLATE_SUFFIX = ".templar.py"

    def __init__(
        self,
        config,
        templates_dir: Path,
        themes_dir: Path,
        static_dir: Path,
        cli = None
    ):
        super().__init__(
            config,
            templates_dir,
            themes_dir,
            static_dir,
        )

        self.cli = cli

        css_path = Path(__file__).resolve().parent / "static" / "studio.css"

        self.studio_css = (
            css_path.read_text(encoding="utf-8") if css_path.is_file() else ""
        )

    def render_template(
        self,
        template_name_or_file,
        user_input=None,
        debug=True,
        **context,
    ):
        template_name = Path(str(template_name_or_file)).name

        if not (template_name.startswith(self.STUDIO_PREFIX) and template_name.endswith(self.TEMPLATE_SUFFIX)):
            return super().render_template(
                template_name_or_file,
                user_input=user_input,
                debug=debug,
                **context,
            )

        page_id = template_name[len(self.STUDIO_PREFIX):-len(self.TEMPLATE_SUFFIX)]

        page = build_studio_page(page_id=page_id, cli=self.cli)

        head = Head([
            Meta(charset="UTF-8"),
            Meta(name="viewport", value="width=device-width, initial-scale=1.0"),
            Title(content=f"Templar Studio — {page_id.replace('-', ' ').title()}"),
            Style(content=self.studio_css),
        ])

        document = Html(
            [head, Body(page)],
            id="templar-root",
            lang="en",
        )

        matrix = ElementMatrix()
        matrix.build(document, f"studio-{page_id}")
        self._request_matrix.set(matrix)

        html_output = "<!DOCTYPE html>\n" + document.render()

        return self._inject_optional_reset_css(html_output)