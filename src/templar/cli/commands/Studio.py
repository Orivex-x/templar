from pathlib import Path

from templar.Router import Router
from templar.TemplarServer import TemplarServer
from templar.cli.BaseCommand import BaseCommand
from templar.studio.navigation import NAVIGATION_ITEMS
from templar.studio.StudioRenderer import StudioRenderer

class Studio(BaseCommand):
    name = "studio"
    help = "Launch Templar Studio"

    def run(self, args, extra_args=None):
        config = self.cli.config
        active_config = config.get_active_config()
        studio_port = int(active_config.get("studio_port", 8765))

        project_dir = Path.cwd().resolve()

        templates_dir = project_dir / "templates"
        themes_dir = project_dir / "themes"
        static_dir = project_dir / "static"

        router = Router(config)

        router.add("/studio", "__templar_studio_overview")

        for item in NAVIGATION_ITEMS:
            router.add(f"/studio/{item.id}", f"__templar_studio_{item.id}")

        renderer = StudioRenderer(
            config,
            templates_dir,
            themes_dir,
            static_dir,
            cli=self.cli
        )

        server = TemplarServer(
            config=config,
            output=self.output,
            router=router,
            renderer=renderer,
            templates_dir=templates_dir,
            themes_dir=themes_dir,
            static_dir=static_dir,
            port_override=studio_port
        )

        host, port = server.server_address
        display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host

        print(f"Templar Studio running at http://{display_host}:{port}/studio")

        server.start()