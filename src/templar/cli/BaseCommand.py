import sys

from templar.cli.CliOutput import CliOutput

sys.dont_write_bytecode = True

class BaseCommand:
    """
    Base class for all Templar CLI commands.

    Provides:
    - Access to the parent TemplarCLI instance via self.cli
    - Access to a centralized Output instance via self.output
    - Shared _run method for standardized behavior
    """

    # Each subclass should define these
    name: str = ""
    help: str = ""
    
    # Allow commands to define their own argparse add_args method
    add_args = None

    def __init__(self, cli=None):
        """
        Initialize the command.

        Args:
            cli (TemplarCLI, optional): The parent CLI instance.
        """
        self.cli = cli
        self.output = cli.output if cli else CliOutput()

    def run(self, args, extra_args=None):
        """
        The main method each command must implement.

        Args:
            args: The argparse.Namespace object with parsed arguments.
            extra_args: Any extra unknown arguments passed.
        """
        raise NotImplementedError("Each command must implement its own run() method.")

    def _run(self, action: str, **kwargs) -> None:
        """
        Shared helper for marketplace-style commands.

        Args:
            action: The marketplace action (install, publish, sign, verify)
            kwargs: Additional parameters
        """
        try:
            from templar.Marketplace import run_marketplace_command

            result = run_marketplace_command(action, config=self.cli.config if self.cli else None, **kwargs)

            from rich.text import Text

            content = Text()
            content.append(f"Action: {action}\n", style="bold magenta")

            for k, v in kwargs.items():
                content.append(f"{k}: ", style="magenta")
                content.append("[hidden]\n" if "passphrase" in k.lower() else f"{v}\n", style="green")

            if result is not None:
                content.append("Result: ", style="magenta")
                content.append(f"{result}\n", style="green")

            content.append("\n[✔] Completed successfully!", style="bold green")

            self.output.panel(content, title=f"Marketplace {action.capitalize()}")

            return result

        except Exception as e:
            self.output.error(str(e), title="Marketplace Error")
            sys.exit(2)
