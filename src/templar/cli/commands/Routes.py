import sys
from pathlib import Path
from typing import Any

from rich.text import Text

from templar.Router import Router
from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True

class RoutesCommand(BaseCommand):
    name = "routes"
    help = "List all registered routes dynamically"

    def _auto_map_templates(self, router: Router, templates_dir: Path) -> None:
        if not templates_dir.exists():
            return

        for template_file in templates_dir.rglob("*.templar.py"):
            name = (
                template_file.relative_to(templates_dir)
                .with_suffix("")
                .with_suffix("")
                .as_posix()
            )
            route = "/" if name == router.default_route else f"/{name}"

            try:
                router.add(route, name)
            except ValueError:
                pass

    def _get_route_rows(
        self,
        router: Router,
        templates_dir: Path,
    ) -> list[dict[str, Any]]:
        rows = []

        for pattern, tpl_file in sorted(
            router.routes.items(),
            key=lambda item: item[0].pattern,
        ):
            template_name = tpl_file.replace(".templar.py", "")

            rows.append({
                "pattern": pattern.pattern,
                "template_file": tpl_file,
                "is_default": template_name == router.default_route,
                "exists": (templates_dir / tpl_file).is_file(),
            })

        return rows

    def _format_cli_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> list[list[str | Text]]:
        formatted_rows = []

        for row in rows:
            formatted_rows.append([
                row["pattern"],
                row["template_file"],
                self._format_flag(row["is_default"]),
                self._format_flag(row["exists"]),
            ])

        return formatted_rows

    @staticmethod
    def _format_flag(flag: bool) -> Text:
        return (
            Text("Yes", style="bold green")
            if flag
            else Text("No", style="bold red")
        )

    def run(
        self,
        args,
        extra_args=None,
        *,
        return_rows: bool = False,
    ) -> list[dict[str, Any]] | None:
        if extra_args:
            self.output.error(
                f"Unrecognized arguments: {' '.join(extra_args)}"
            )
            sys.exit(1)

        config = self.cli.config.get_active_config()
        router = Router(config=config)

        templates_dir = Path(
            self.cli.config.get("templates_dir")
        ).resolve()

        self._auto_map_templates(
            router=router,
            templates_dir=templates_dir,
        )

        app_path = Path("app.py").resolve()

        if app_path.exists():
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "app",
                str(app_path),
            )

            if spec and spec.loader:
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)

                app_router = getattr(app_module, "router", None)

                if isinstance(app_router, Router):
                    router.merge(app_router)

        if not router.routes:
            if not return_rows:
                self.output.warning(
                    "No routes registered yet.",
                    title="Routes",
                )

            return []

        rows = self._get_route_rows(
            router=router,
            templates_dir=templates_dir,
        )

        if return_rows:
            return rows

        self.output.table(
            columns=[
                Text("Route Pattern", style="bold magenta"),
                Text("Template File", style="bold magenta"),
                Text("Default", style="bold magenta"),
                Text("Exists", style="bold magenta"),
            ],
            rows=self._format_cli_rows(rows),
            title="Routes Overview",
            column_styles=["cyan", "green", "magenta", "red"],
        )

        return None