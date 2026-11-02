import sys, argparse, argcomplete, importlib, inspect
from pathlib import Path
from rich.console import Console

from templar.Config import Config
from templar.cli.BaseCommand import BaseCommand
from templar.cli.CliOutput import CliOutput
from templar.cli.Utils import print_rich_help

sys.dont_write_bytecode = True

class TemplarCLI:
    COMMAND_FOLDER = Path(__file__).parent / "commands"

    def __init__(self) -> None:
        # Core CLI properties
        self.console = Console()
        self.output = CliOutput(self.console)
        self.config = Config()

        # Argument parser setup
        self.parser = argparse.ArgumentParser(
            prog="templar",
            description="Templar CLI",
            add_help=False
        )
        self.parser.error = lambda message: self._render_parse_error(self.parser, message)

        self.parser.add_argument("-h", "--help", action="store_true", help="Show this help message")
        self.subparsers = self.parser.add_subparsers(dest="command")
        self.marketplace_subparsers = None

        # Register commands dynamically
        self._register_commands()

        argcomplete.autocomplete(self.parser)

    def _register_commands(self) -> None:
        """Automatically find and register all BaseCommand subclasses in commands/"""
        registered_commands = set()

        def add_help_arg(parser, command_name):
            parser.add_argument("-h", "--help", action="store_true", help=f"Show help for '{command_name}'")

        marketplace_parser = self.subparsers.add_parser(
            "marketplace",
            help="Manage marketplace packages",
            add_help=False,
        )
        marketplace_parser.add_argument(
            "-h", "--help", action="store_true", help="Show help for 'marketplace'"
        )
        self.marketplace_subparsers = marketplace_parser.add_subparsers(dest="marketplace_action")

        def add_command(name, func, help_text, args=None):
            if name in registered_commands:
                self.output.error(f"Command '{name}' is already registered. Skipping duplicate.")

                return
            
            registered_commands.add(name)
            parser = self.subparsers.add_parser(name, help=help_text, add_help=False)
            parser.error = lambda message, parser=parser: self._render_parse_error(parser, message)
            
            add_help_arg(parser, name)
            
            if args:
                args(parser)

            parser.set_defaults(func=func)

            if name.startswith("marketplace-"):
                marketplace_name = name.removeprefix("marketplace-")
                marketplace_command = self.marketplace_subparsers.add_parser(
                    marketplace_name,
                    help=help_text,
                    add_help=False,
                )
                marketplace_command.error = lambda message, parser=marketplace_command: self._render_parse_error(
                    parser, message
                )
                add_help_arg(marketplace_command, f"marketplace {marketplace_name}")

                if args:
                    args(marketplace_command)

                marketplace_command.set_defaults(func=func)

        for cmd_file in self.COMMAND_FOLDER.glob("*.py"):
            if cmd_file.name.startswith("__"):
                continue

            # Import by full package path
            module_name = f"templar.cli.commands.{cmd_file.stem}"
            module = importlib.import_module(module_name)

            # Iterate through attributes
            for attr_name in dir(module):
                obj = getattr(module, attr_name)

                if inspect.isclass(obj) and issubclass(obj, BaseCommand) and obj is not BaseCommand:
                    cmd_instance = obj(self)
                    add_args = getattr(obj, "add_args", None)

                    add_command(getattr(obj, "name"), cmd_instance.run, getattr(obj, "help"), add_args)

    def _render_parse_error(self, parser, message: str) -> None:
        """Keep argparse validation failures in the same Rich CLI presentation."""
        self.output.error(message, title="Templar CLI")
        print_rich_help(parser, self.console)

        raise SystemExit(2)

    def run(self) -> None:
        raw_args = sys.argv[1:]

        if "-h" in raw_args or "--help" in raw_args:
            parser = self.parser

            for argument in raw_args:
                subparsers = next(
                    (action for action in parser._actions if isinstance(action, argparse._SubParsersAction)),
                    None,
                )

                if subparsers and argument in subparsers.choices:
                    parser = subparsers.choices[argument]

            print_rich_help(parser, self.console)

            return

        args, extra_args = self.parser.parse_known_args()
        
        try:
            if getattr(args, "help", False):
                parser = self.subparsers.choices.get(getattr(args, "command", None), self.parser)

                if getattr(args, "marketplace_action", None):
                    parser = self.marketplace_subparsers.choices.get(args.marketplace_action, parser)

                print_rich_help(parser, self.console)

                return

            if not hasattr(args, "func"):
                if getattr(args, "command", None) == "marketplace":
                    print_rich_help(self.subparsers.choices["marketplace"], self.console)
                    return

                self.output.error(f"Unknown command: {getattr(args, 'command', None)}")
                print_rich_help(self.parser, self.console)
                sys.exit(1)

            args.func(args, extra_args=extra_args)

        except KeyboardInterrupt:
            self.output.panel("\nAborted by user.", border_style="red")
            sys.exit(130)
        except Exception as e:
            self.output.error(f"Unexpected error: {e}")
            sys.exit(2)

def main():
    TemplarCLI().run()

if __name__ == "__main__":
    main()
