import sys, code
from pathlib import Path
from templar.Renderer import Renderer
from templar.Router import Router
from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True

try:
    from IPython.terminal.embed import InteractiveShellEmbed
    from traitlets.config import Config as IPConfig
    HAVE_IPYTHON = True
except ImportError:
    HAVE_IPYTHON = False

class ShellCommand(BaseCommand):
    name = "shell"
    help = "Interactive Templar Python shell"

    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Shell Error")
            sys.exit(1)

        config = self.cli.config
        templates_directory = Path(config.get("templates_dir", "templates")).resolve()
        themes_directory = Path(config.get("themes_dir", "themes")).resolve()
        static_directory = Path(config.get("static_dir", "static")).resolve()
        renderer = Renderer(config, templates_directory, themes_directory, static_directory)
        router = Router(config)

        banner_content = "Available Objects:\n\n- renderer\n- router\n- config\n- templates_directory\n- themes_directory\n- static_directory"
        self.output.banner("Templar Interactive Shell", content=banner_content)

        local_ns = {
            "renderer": renderer,
            "router": router,
            "config": config,
            "templates_directory": templates_directory,
            "themes_directory": themes_directory,
            "static_directory": static_directory,
        }

        if HAVE_IPYTHON:
            cfg = IPConfig()
            cfg.TerminalInteractiveShell.highlighting_style = "monokai"
            ipshell = InteractiveShellEmbed(banner1="", config=cfg, exit_msg="")
            ipshell(local_ns=local_ns)
        else:
            sys.displayhook = (
                lambda value: self.output.text(str(value), style="green")
                if value is not None
                else None
            )
            code.interact(banner="", local=local_ns)

        self.output.exit()
