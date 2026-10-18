import sys
from templar.cli.BaseCommand import BaseCommand
from templar.cli.Utils import print_rich_help

sys.dont_write_bytecode = True

class HelpCommand(BaseCommand):
    name = "help"
    help = "Show help for a command"

    @staticmethod
    def add_args(parser):
        parser.add_argument("command_name", nargs="?", help="Command to show help for")

    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Templar Help")
            sys.exit(1)

        cmd_name = getattr(args, "command_name", None)

        if cmd_name:
            subparser = self.cli.subparsers.choices.get(cmd_name)

            if subparser:
                print_rich_help(subparser, self.cli.console)
            else:
                self.output.error(f"No such command: {cmd_name}", title="Templar Help")
                sys.exit(1)
        else:
            print_rich_help(self.cli.parser, self.cli.console)
