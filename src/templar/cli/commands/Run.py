import sys
import importlib.util
from pathlib import Path
from rich.text import Text
from rich.console import Group

from templar.TemplarServer import TemplarServer
from templar.Renderer import Renderer
from templar.Router import Router
from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True

def auto_map_templates(router: Router, templates_dir: Path, output=None) -> None:
    """
    Automatically register all user templates (*.templar.py) as routes.
    - 'index.templar.py' -> '/'
    - others -> '/<name>'
    """
    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    for template_file in templates_dir.rglob("*.templar.py"):
        name = template_file.relative_to(templates_dir).with_suffix("").with_suffix("").as_posix()
        route = "/" if name == "index" else f"/{name}"
        
        try:
            router.add(route, name)
        except ValueError as e:
            if output:
                output.warning(str(e), title="Route Warning")

class RunCommand(BaseCommand):
    name = "run"
    help = "Run the Templar server"

    @staticmethod
    def add_args(parser):
        parser.add_argument("--prod", action="store_true", help="Force production mode")
        parser.add_argument("--host", default=None, help="Server host")
        parser.add_argument("--port", type=int, default=None, help="Server port")
        parser.add_argument("--theme", default=None, help="Theme to use")

    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}")
            sys.exit(1)

        # -------------------
        # Load configuration
        # -------------------
        config = self.cli.config
        active_env = "prod" if getattr(args, "prod", False) else config.active_env
        config.set_active_config(active_env, persist=False)
        active_config = config.get_active_config()

        # -------------------
        # Paths and options
        # -------------------
        project_root = Path.cwd()  # User project root
        templates_directory = Path(active_config.get("templates_dir", "templates"))
        templates_directory = (project_root / templates_directory).resolve()

        themes_directory = Path(active_config.get("themes_dir", "themes"))
        themes_directory = (project_root / themes_directory).resolve()

        static_directory = Path(active_config.get("static_dir", "static"))
        static_directory = (project_root / static_directory).resolve()

        theme = getattr(args, "theme", None) or active_config.get("theme", "light")
        host = getattr(args, "host", None) or active_config.get("host", "0.0.0.0")
        port = getattr(args, "port", None) or active_config.get("port", 8000)

        for key, value in {"theme": theme, "host": host, "port": port}.items():
            config.override(key, value)

        default_route = active_config.get("default_route", "index")
        display_mode = "Production" if active_env == "prod" else "Development"

        # -------------------
        # Initialize engine
        # -------------------
        renderer = Renderer(config, templates_directory, themes_directory, static_directory)
        router = Router(config=config)

        # Automatically map user templates
        auto_map_templates(router, templates_directory, self.output)

        # -------------------
        # Load optional app.py router
        # -------------------
        app_path = Path("app.py").resolve()

        if app_path.exists():
            spec = importlib.util.spec_from_file_location("app", str(app_path))

            if spec and spec.loader:
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)
                app_router = getattr(app_module, "router", None)
                
                if isinstance(app_router, Router):
                    # Keep convention-based template routes and let explicit application definitions override matching patterns.
                    router.merge(app_router)

        # -------------------
        # Display server info
        # -------------------
        info_text = [
            Text.assemble(("Mode: ", "magenta"), (display_mode, "green")),
            Text.assemble(("Host: ", "magenta"), (host, "green")),
            Text.assemble(("Port: ", "magenta"), (str(port), "green")),
            Text.assemble(("Templates: ", "magenta"), (str(templates_directory), "green")),
            Text.assemble(("Theme: ", "magenta"), (theme, "green")),
            Text.assemble(("Default Route: ", "magenta"), (f"{default_route}\n", "green")),
            Text.assemble(("Templar server is running at ", "magenta"), (f"{'https' if active_config.get('ssl_cert_path') and active_config.get('ssl_key_path') else 'http'}://{host}:{port}/{default_route}", "green"))
        ]

        self.output.panel(Group(*info_text), title="Templar Server")

        # -------------------
        # Start server
        # -------------------
        server = TemplarServer(
            config=config,
            output=self.output,
            router=router,
            renderer=renderer,
            templates_dir=templates_directory,
            themes_dir=themes_directory,
            static_dir=static_directory
        )

        server.start()

        if server.interrupted:
            self.output.panel([
                Text("Templar server shutdown gracefully", style="red")
            ], title="Templar Server", border_style="red")
