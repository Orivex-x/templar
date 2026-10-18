import sys
from pathlib import Path
from rich.syntax import Syntax

from templar.Renderer import Renderer
from templar.cli.Utils import prettify_html
from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True


class PreviewCommand(BaseCommand):
    name = "preview"
    help = "Preview a template"

    @staticmethod
    def add_args(parser):
        parser.add_argument("template", help="Template file to preview (without .templar.py)")
        parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(
                f"Unrecognized arguments: {' '.join(extra_args)}",
                title="Preview Error"
            )
            sys.exit(1)

        # --------------------------------
        # Activate environment
        # --------------------------------
        config = self.cli.config
        active_config = config.get_active_config()

        # --------------------------------
        # Resolve project paths
        # --------------------------------
        project_root = Path(active_config.get("project_root", Path.cwd())).resolve()

        templates_dir = Path(active_config.get("templates_dir", project_root / "templates")).resolve()
        themes_dir = Path(active_config.get("themes_dir", project_root / "themes")).resolve()
        static_dir = Path(active_config.get("static_dir", project_root / "static")).resolve()

        # --------------------------------
        # Initialize renderer
        # --------------------------------
        renderer = Renderer(config, templates_dir, themes_dir, static_dir)

        try:
            html = renderer.render_template(args.template, debug=args.debug)
            pretty_html = prettify_html(html)
            syntax = Syntax(
                pretty_html,
                "html",
                theme="monokai",
                line_numbers=True
            )

            self.output.panel(
                syntax,
                title=f"Preview: {args.template}"
            )
        except Exception as e:
            if args.debug or active_config.get("debug", False):
                raise

            self.output.error(
                f"Failed to render template: {e}",
                title="Preview Error"
            )
            sys.exit(2)
